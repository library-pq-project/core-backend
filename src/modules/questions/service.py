import json
import logging
from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader

try:
    import httpx
except Exception:  # noqa: BLE001
    httpx = None

from src.common.errors import bad_request, not_found
from src.common.utils import generate_slug, now_utc
from src.core.config import settings
from src.modules.academic.models import Assessment
from src.modules.questions.models import Question, QuestionImportJob, QuestionOption
from src.modules.questions.repository import QuestionRepository
from src.modules.questions.schemas import (
    BulkImportResult,
    BulkQuestionImportRequest,
    BulkQuestionRow,
    ImportRowError,
    QuestionCreate,
    QuestionImportJobRead,
    QuestionUpdate,
)
from src.modules.topics.categorization import TopicCategorizationService
from src.modules.topics.models import Topic
from src.modules.topics.repository import TopicRepository

logger = logging.getLogger(__name__)


class QuestionService:
    def __init__(self, repository: QuestionRepository, topic_repository: TopicRepository):
        self.repository = repository
        self.topic_repository = topic_repository
        self.topic_categorizer = TopicCategorizationService(topic_repository)

    def list_questions(
        self,
        *,
        assessment_id: int | None,
        course_id: int | None,
        topic_id: int | None,
        year: int | None,
        question_type: str | None,
        source_type: str | None,
        skip: int,
        limit: int,
    ) -> list[Question]:
        return self.repository.list(
            course_id=course_id,
            assessment_id=assessment_id,
            topic_id=topic_id,
            year=year,
            question_type=question_type,
            source_type=source_type,
            skip=skip,
            limit=limit,
        )

    def get_question(self, question_id: int) -> Question:
        question = self.repository.get(question_id)
        if not question:
            raise not_found("question", question_id)
        return question

    def create_question(self, payload: QuestionCreate) -> Question:
        if payload.assessment_id is None:
            raise bad_request("assessment_id is required", error_code="ASSESSMENT_ID_REQUIRED")
        assessment = self.repository.get_assessment(payload.assessment_id)
        if assessment is None:
            raise not_found("assessment", payload.assessment_id)
        derived_course_id = assessment.course_id
        if payload.course_id is not None and payload.course_id != derived_course_id:
            raise bad_request(
                f"course_id {payload.course_id} does not match assessment {assessment.id}. Omit course_id or use course_id {derived_course_id}.",
                error_code="COURSE_ASSESSMENT_MISMATCH",
                resource="assessment",
                resource_id=assessment.id,
            )
        source_text = payload.source_text or payload.question_text
        if source_text is None:
            raise bad_request(
                "Either source_text or question_text is required to create a question",
                error_code="QUESTION_TEXT_REQUIRED",
            )
        if payload.topic_id is not None:
            topic = self.topic_repository.get(payload.topic_id)
            if topic is None:
                raise not_found("topic", payload.topic_id)
            if topic.course_id != derived_course_id:
                raise bad_request(
                    f"Topic with id {payload.topic_id} does not belong to course with id {derived_course_id}",
                    error_code="TOPIC_COURSE_MISMATCH",
                    resource="topic",
                    resource_id=payload.topic_id,
                )
        if payload.lecture_note_id is not None:
            lecture_note = self.repository.get_lecture_note(payload.lecture_note_id)
            if lecture_note is None:
                raise not_found("lecture_note", payload.lecture_note_id)
            if lecture_note.course_id != derived_course_id:
                raise bad_request(
                    f"Lecture note with id {payload.lecture_note_id} does not belong to course with id {derived_course_id}",
                    error_code="LECTURE_NOTE_COURSE_MISMATCH",
                    resource="lecture_note",
                    resource_id=payload.lecture_note_id,
                )
        question = Question(
            assessment_id=payload.assessment_id,
            course_id=derived_course_id,
            topic_id=payload.topic_id,
            lecture_note_id=payload.lecture_note_id,
            year=payload.year,
            question_text=payload.question_text or source_text,
            source_text=source_text,
            content_format=payload.content_format,
            question_type=payload.question_type,
            source_type=payload.source_type,
            difficulty_level=payload.difficulty_level,
            mark_allocation=payload.mark_allocation,
            marking_scheme=payload.marking_scheme,
            solution_text=payload.solution_text,
            explanation=payload.explanation,
            is_active=payload.is_active,
        )
        question.options = [
            QuestionOption(
                option_text=item.option_text,
                is_correct=item.is_correct,
                position=item.position,
            )
            for item in payload.options
        ]
        return self.repository.create(question)

    def update_question(self, question_id: int, payload: QuestionUpdate) -> Question:
        question = self.get_question(question_id)
        updates = payload.model_dump(exclude_unset=True)

        if "assessment_id" in updates:
            assessment_id = updates["assessment_id"]
            if assessment_id is None:
                raise bad_request(
                    "assessment_id cannot be removed from an existing question",
                    error_code="ASSESSMENT_ID_REQUIRED",
                    resource="question",
                    resource_id=question_id,
                )
            assessment = self.repository.get_assessment(assessment_id)
            if assessment is None:
                raise not_found("assessment", assessment_id)
            question.assessment_id = assessment.id
            question.course_id = assessment.course_id
            updates.pop("assessment_id", None)

        if "course_id" in updates:
            requested_course_id = updates.pop("course_id")
            if requested_course_id is not None and requested_course_id != question.course_id:
                raise bad_request(
                    f"course_id is derived from assessment_id and cannot be changed directly for question with id {question_id}",
                    error_code="COURSE_DERIVED_FROM_ASSESSMENT",
                    resource="question",
                    resource_id=question_id,
                )

        for field in [
            "topic_id",
            "lecture_note_id",
            "year",
            "question_text",
            "source_text",
            "content_format",
            "question_type",
            "source_type",
            "difficulty_level",
            "mark_allocation",
            "marking_scheme",
            "solution_text",
            "explanation",
            "is_active",
        ]:
            if field in updates:
                setattr(question, field, updates[field])

        if "topic_id" in updates and question.topic_id is not None:
            topic = self.topic_repository.get(question.topic_id)
            if topic is None:
                raise not_found("topic", question.topic_id)
            if topic.course_id != question.course_id:
                raise bad_request(
                    f"Topic with id {question.topic_id} does not belong to course with id {question.course_id}",
                    error_code="TOPIC_COURSE_MISMATCH",
                    resource="topic",
                    resource_id=question.topic_id,
                )

        if "lecture_note_id" in updates and question.lecture_note_id is not None:
            lecture_note = self.repository.get_lecture_note(question.lecture_note_id)
            if lecture_note is None:
                raise not_found("lecture_note", question.lecture_note_id)
            if lecture_note.course_id != question.course_id:
                raise bad_request(
                    f"Lecture note with id {question.lecture_note_id} does not belong to course with id {question.course_id}",
                    error_code="LECTURE_NOTE_COURSE_MISMATCH",
                    resource="lecture_note",
                    resource_id=question.lecture_note_id,
                )

        if "options" in updates and payload.options is not None:
            question.options = [
                QuestionOption(
                    option_text=item.option_text,
                    is_correct=item.is_correct,
                    position=item.position,
                )
                for item in payload.options
            ]

        return self.repository.save(question)

    def delete_question(self, question_id: int) -> None:
        question = self.get_question(question_id)
        self.repository.delete(question)

    def _validate_objective_options(self, row: BulkQuestionRow) -> None:
        if not row.options:
            raise ValueError("objective question requires options")
        if len(row.options) < 2:
            raise ValueError("objective question requires at least 2 options")
        correct_count = sum(1 for option in row.options if option.is_correct)
        if correct_count != 1:
            raise ValueError("objective question requires exactly 1 correct option")

    def _apply_mode_defaults(
        self,
        *,
        row: BulkQuestionRow,
        import_mode: str,
        default_course_id: int | None,
        default_assessment_id: int | None,
        default_source_type: str,
    ) -> BulkQuestionRow:
        merged = row.model_copy(deep=True)
        if merged.course_id is None:
            merged.course_id = default_course_id
        if merged.assessment_id is None:
            merged.assessment_id = default_assessment_id
        if merged.source_type is None:
            merged.source_type = default_source_type

        if import_mode == "objective":
            merged.question_type = "objective"
        elif import_mode == "theory":
            merged.question_type = "theory"

        return merged

    def _default_question_format(self, import_mode: str) -> str:
        return {
            "objective": "Objective",
            "theory": "Theory",
            "mixed": "Mixed",
        }.get(import_mode, "Mixed")

    def _default_assessment_type_from_file_name(self, file_name: str | None) -> str:
        stem = Path(file_name or "questions").stem.lower()
        if any(token in stem for token in ["mid", "test", "ca", "continuous"]):
            return "Test"
        if "quiz" in stem:
            return "Quiz"
        return "Exam"

    def _ensure_default_assessment(
        self,
        *,
        payload: BulkQuestionImportRequest,
        user_id: int,
        file_name: str | None,
    ) -> int | None:
        if payload.default_assessment_id is not None:
            assessment = self.repository.get_assessment(payload.default_assessment_id)
            if assessment is None:
                raise not_found("assessment", payload.default_assessment_id)
            if payload.default_course_id is not None and payload.default_course_id != assessment.course_id:
                raise bad_request(
                    f"default_course_id {payload.default_course_id} does not match assessment {assessment.id}. Omit default_course_id or use course_id {assessment.course_id}.",
                    error_code="COURSE_ASSESSMENT_MISMATCH",
                    resource="assessment",
                    resource_id=assessment.id,
                )
            payload.default_course_id = assessment.course_id
            return assessment.id

        if not payload.rows:
            return None

        if payload.default_course_id is None:
            raise bad_request(
                "default_course_id is required when bulk-upload should create a new assessment automatically.",
                error_code="DEFAULT_COURSE_ID_REQUIRED",
                resource="course",
            )

        course = self.repository.get_course(payload.default_course_id)
        if course is None:
            raise not_found("course", payload.default_course_id)

        active_calendar = self.repository.get_active_calendar()
        academic_session_id = payload.default_academic_session_id or (
            active_calendar.academic_session_id if active_calendar is not None else None
        )
        semester_id = payload.default_semester_id if payload.default_semester_id is not None else (
            active_calendar.semester_id if active_calendar is not None else None
        )

        if academic_session_id is None:
            raise bad_request(
                "default_academic_session_id is required when no active academic calendar is configured.",
                error_code="ACADEMIC_SESSION_REQUIRED",
                resource="academic_session",
            )

        session = self.repository.get_session(academic_session_id)
        if session is None:
            raise not_found("academic_session", academic_session_id)

        if semester_id is not None:
            semester = self.repository.get_semester(semester_id)
            if semester is None:
                raise not_found("semester", semester_id)

        assessment_type = payload.default_assessment_type or self._default_assessment_type_from_file_name(file_name)
        question_format = payload.default_question_format or self._default_question_format(payload.import_mode)
        year_label = session.name
        timestamp = now_utc().strftime("%Y%m%d%H%M%S")
        slug = generate_slug(
            f"{course.id}-{academic_session_id}-{semester_id}-{assessment_type}-{question_format}-{year_label}-{timestamp}"
        )

        assessment = self.repository.create_assessment(
            Assessment(
                course_id=course.id,
                academic_session_id=academic_session_id,
                semester_id=semester_id,
                assessment_type=assessment_type,
                question_format=question_format,
                default_duration_minutes=payload.default_duration_minutes,
                year_label=year_label,
                source_type=payload.default_source_type,
                created_by_user_id=user_id,
                slug=slug,
            )
        )
        payload.default_course_id = course.id
        payload.default_assessment_id = assessment.id
        return assessment.id

    def _resolve_topic(self, row: BulkQuestionRow, *, auto_categorize_topics: bool) -> tuple[int | None, float | None, dict | None, int | None]:
        if row.course_id is None:
            return None, None, None, None

        if row.topic_id is not None:
            existing = self.topic_repository.get(row.topic_id)
            if existing is None:
                raise ValueError(f"topic_id={row.topic_id} not found")
            if existing.course_id != row.course_id:
                raise ValueError(f"topic_id={row.topic_id} does not belong to course_id={row.course_id}")
            return existing.id, None, {"strategy": "provided_topic_id"}, None

        if row.topic_name:
            slug = generate_slug(row.topic_name)
            existing_by_slug = self.topic_repository.get_by_course_and_slug(course_id=row.course_id, slug=slug)
            if existing_by_slug is not None:
                return existing_by_slug.id, 1.0, {"strategy": "provided_topic_name_matched", "topic_slug": slug}, None

            created = self.topic_repository.create(
                Topic(
                    course_id=row.course_id,
                    name=row.topic_name.strip(),
                    slug=slug,
                    description="Created from bulk upload topic_name",
                )
            )
            return created.id, 1.0, {"strategy": "provided_topic_name_created", "topic_slug": slug}, created.id

        if auto_categorize_topics:
            topic_id, confidence, trace = self.topic_categorizer.classify_question_topic(
                course_id=row.course_id,
                question_text=row.question_text or row.source_text or "",
                allowed_topic_ids=None,
            )
            return topic_id, confidence, trace, topic_id if trace and "created_new_topic" in str(trace.get("strategy")) else None

        return None, None, {"strategy": "topic_unset"}, None

    def _build_question_from_row(
        self,
        row: BulkQuestionRow,
        *,
        draft_theory_without_solution: bool,
        auto_categorize_topics: bool,
    ) -> tuple[Question, int | None]:
        if row.course_id is None:
            raise ValueError("course_id is required")
        if row.assessment_id is None:
            raise ValueError("assessment_id is required")

        source_text = row.source_text or row.question_text
        if not source_text:
            raise ValueError("Either source_text or question_text is required")

        if row.question_type is None:
            raise ValueError("question_type is required")

        if row.question_type == "objective":
            self._validate_objective_options(row)
        elif row.question_type == "theory":
            if not row.marking_scheme:
                raise ValueError("theory question requires marking_scheme")
            if not draft_theory_without_solution and not row.solution_text:
                raise ValueError("theory question requires solution_text unless draft mode is enabled")

        topic_id, confidence, trace, created_topic_id = self._resolve_topic(
            row,
            auto_categorize_topics=auto_categorize_topics,
        )

        question = Question(
            assessment_id=row.assessment_id,
            course_id=row.course_id,
            topic_id=topic_id,
            lecture_note_id=row.lecture_note_id,
            year=row.year,
            question_text=row.question_text or source_text,
            source_text=source_text,
            content_format=row.content_format,
            question_type=row.question_type,
            source_type=row.source_type or "actual",
            difficulty_level="medium" if row.difficulty_level == "mixed" else row.difficulty_level,
            mark_allocation=row.mark_allocation,
            marking_scheme=row.marking_scheme,
            solution_text=row.solution_text,
            explanation=row.explanation,
            ai_topic_confidence=confidence,
            ai_topic_trace=trace,
            is_active=row.is_active,
        )
        if row.question_type == "objective":
            question.options = [
                QuestionOption(
                    option_text=option.option_text,
                    is_correct=option.is_correct,
                    position=option.position,
                )
                for option in row.options
            ]
        return question, created_topic_id

    def _normalize_row_from_file(self, raw: dict) -> dict:
        payload = {key: value for key, value in raw.items() if key is not None}

        options = payload.get("options")
        if isinstance(options, str) and options.strip():
            try:
                parsed_options = json.loads(options)
                if isinstance(parsed_options, list):
                    payload["options"] = parsed_options
            except Exception:
                pass

        if isinstance(payload.get("options"), list):
            normalized_options = []
            for index, option in enumerate(payload["options"], start=1):
                if not isinstance(option, dict):
                    normalized_options.append(option)
                    continue

                normalized_option = dict(option)
                raw_position = normalized_option.get("position")
                normalized_position: int | None = None

                if isinstance(raw_position, int):
                    normalized_position = raw_position
                elif isinstance(raw_position, str):
                    stripped = raw_position.strip()
                    if stripped.isdigit():
                        normalized_position = int(stripped)
                    elif len(stripped) == 1 and stripped.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                        normalized_position = ord(stripped.upper()) - ord("A") + 1

                if normalized_position is None:
                    normalized_position = index

                normalized_option["position"] = normalized_position
                normalized_options.append(normalized_option)

            payload["options"] = normalized_options

        option_columns = []
        for label in ["a", "b", "c", "d", "e", "f"]:
            value = payload.get(f"option_{label}")
            if value is not None and str(value).strip():
                option_columns.append((label.upper(), str(value).strip()))

        if option_columns and not payload.get("options"):
            correct_position = payload.get("correct_option_position")
            correct_label = str(payload.get("correct_option_label") or "").strip().upper()
            try:
                correct_position_value = int(correct_position) if correct_position not in [None, ""] else None
            except Exception:
                correct_position_value = None

            generated_options = []
            for index, (label, option_text) in enumerate(option_columns, start=1):
                is_correct = False
                if correct_position_value is not None and correct_position_value == index:
                    is_correct = True
                if correct_label and correct_label == label:
                    is_correct = True
                generated_options.append(
                    {
                        "option_text": option_text,
                        "is_correct": is_correct,
                        "position": index,
                    }
                )
            payload["options"] = generated_options

        return payload

    def _extract_text_from_upload(self, *, file_name: str, content: bytes) -> tuple[str, str]:
        extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if extension == "txt":
            return content.decode("utf-8", errors="ignore"), extension
        if extension == "pdf":
            reader = PdfReader(BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text, extension
        if extension == "docx":
            document = Document(BytesIO(content))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            return text, extension
        raise bad_request(
            "Unsupported AI bulk upload file type. Use pdf, docx, or txt.",
            error_code="UNSUPPORTED_UPLOAD_TYPE",
        )

    def _fallback_document_rows(self, *, extracted_text: str, import_mode: str) -> list[dict]:
        blocks = [block.strip() for block in extracted_text.split("\n\n") if block.strip()]
        rows: list[dict] = []
        for block in blocks[: settings.BULK_IMPORT_MAX_ROWS]:
            if import_mode == "objective":
                rows.append(
                    {
                        "question_text": block,
                        "source_text": block,
                        "question_type": "objective",
                        "options": [
                            {"option_text": "Option A", "is_correct": True, "position": 1},
                            {"option_text": "Option B", "is_correct": False, "position": 2},
                        ],
                    }
                )
            else:
                rows.append(
                    {
                        "question_text": block,
                        "source_text": block,
                        "question_type": "theory" if import_mode == "theory" else "theory",
                        "marking_scheme": "Review and update marking scheme after import.",
                        "solution_text": "Review and update model solution after import.",
                    }
                )
        return rows

    def _generate_rows_from_document(
        self,
        *,
        extracted_text: str,
        import_mode: str,
        file_name: str,
    ) -> list[dict]:
        if not extracted_text.strip():
            raise bad_request(
                "The uploaded file does not contain extractable text.",
                error_code="EMPTY_UPLOAD_TEXT",
            )

        if not settings.GEMINI_API_KEY or httpx is None:
            if settings.AI_ALLOW_STUB_FALLBACK:
                logger.warning(
                    "AI bulk upload fallback in use file=%s mode=%s has_api_key=%s httpx_available=%s",
                    file_name,
                    import_mode,
                    bool(settings.GEMINI_API_KEY),
                    httpx is not None,
                )
                return self._fallback_document_rows(
                    extracted_text=extracted_text,
                    import_mode=import_mode,
                )
            raise bad_request(
                "AI document bulk upload requires GEMINI_API_KEY and httpx.",
                error_code="AI_BULK_UPLOAD_UNAVAILABLE",
            )

        prompt = (
            "You are converting an exam or question bank document into structured import rows. "
            "Return strict JSON array only. Each array item must be an object with keys: "
            "question_text, source_text, question_type, options, marking_scheme, solution_text, explanation. "
            "For objective questions, options must be a list of objects with keys option_text, is_correct, position. "
            "For theory questions, options must be an empty list. "
            "Do not invent metadata outside the document unless needed to keep the schema valid. "
            "If the document does not clearly reveal the answer for an objective question, choose the best supported answer and include a concise explanation. "
            f"import_mode={import_mode}. "
            f"document_name={file_name}. "
            f"document_text={extracted_text[:20000]}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        last_error: Exception | None = None
        for attempt_index in range(1, settings.GEMINI_MAX_RETRIES + 2):
            try:
                with httpx.Client(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
                    response = client.post(
                        url,
                        json=payload,
                        headers={
                            "x-goog-api-key": settings.GEMINI_API_KEY,
                            "Content-Type": "application/json",
                        },
                    )
                response.raise_for_status()
                data = response.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
                if text.startswith("```"):
                    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                parsed = json.loads(text)
                if not isinstance(parsed, list):
                    raise ValueError("AI bulk upload response must be a JSON array")
                return [dict(item) for item in parsed if isinstance(item, dict)]
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "AI bulk upload parsing failed file=%s mode=%s attempt=%s/%s error=%s",
                    file_name,
                    import_mode,
                    attempt_index,
                    settings.GEMINI_MAX_RETRIES + 1,
                    exc,
                )

        raise bad_request(
            f"AI could not parse the uploaded document into questions: {last_error}",
            error_code="AI_BULK_UPLOAD_PARSE_FAILED",
        )

    def _parse_rows_from_file(self, *, file_name: str, content: bytes, import_mode: str) -> tuple[list[BulkQuestionRow], list[ImportRowError], str]:
        extracted_text, source_type = self._extract_text_from_upload(file_name=file_name, content=content)
        raw_rows = self._generate_rows_from_document(
            extracted_text=extracted_text,
            import_mode=import_mode,
            file_name=file_name,
        )

        if len(raw_rows) > settings.BULK_IMPORT_MAX_ROWS:
            raise bad_request(
                f"Row limit exceeded. Maximum allowed is {settings.BULK_IMPORT_MAX_ROWS}",
                error_code="ROW_LIMIT_EXCEEDED",
            )

        parsed_rows: list[BulkQuestionRow] = []
        errors: list[ImportRowError] = []
        for index, raw in enumerate(raw_rows, start=1):
            try:
                normalized = self._normalize_row_from_file(raw)
                parsed_rows.append(BulkQuestionRow.model_validate(normalized))
            except Exception as exc:  # noqa: BLE001
                errors.append(ImportRowError(row_number=index, errors=[str(exc)]))

        return parsed_rows, errors, source_type

    def _build_job(
        self,
        *,
        user_id: int,
        source_type: str,
        file_name: str | None,
        import_mode: str,
        total_rows: int,
    ) -> QuestionImportJob:
        return self.repository.create_import_job(
            QuestionImportJob(
                created_by_user_id=user_id,
                status="pending",
                source_type=source_type,
                file_name=file_name,
                import_mode=import_mode,
                total_rows=total_rows,
            )
        )

    def _run_bulk_import(
        self,
        *,
        payload: BulkQuestionImportRequest,
        user_id: int,
        source_type: str,
        file_name: str | None,
        parse_errors: list[ImportRowError] | None = None,
    ) -> BulkImportResult:
        parse_errors = parse_errors or []
        created_assessment_id = self._ensure_default_assessment(
            payload=payload,
            user_id=user_id,
            file_name=file_name,
        )
        job = self._build_job(
            user_id=user_id,
            source_type=source_type,
            file_name=file_name,
            import_mode=payload.import_mode,
            total_rows=len(payload.rows),
        )

        created_questions: list[Question] = []
        created_topic_ids: set[int] = set()
        errors: list[ImportRowError] = list(parse_errors)

        for index, row in enumerate(payload.rows, start=1):
            try:
                effective = self._apply_mode_defaults(
                    row=row,
                    import_mode=payload.import_mode,
                    default_course_id=payload.default_course_id,
                    default_assessment_id=payload.default_assessment_id,
                    default_source_type=payload.default_source_type,
                )
                question, created_topic_id = self._build_question_from_row(
                    effective,
                    draft_theory_without_solution=payload.draft_theory_without_solution,
                    auto_categorize_topics=payload.auto_categorize_topics,
                )
                created_questions.append(question)
                if created_topic_id is not None:
                    created_topic_ids.add(created_topic_id)
            except Exception as exc:  # noqa: BLE001
                errors.append(ImportRowError(row_number=index, errors=[str(exc)]))

        accepted_questions = self.repository.create_many(created_questions) if created_questions else []

        accepted_count = len(accepted_questions)
        rejected_count = len(errors)
        job.status = "completed" if rejected_count == 0 else "completed_with_errors"
        job.accepted_count = accepted_count
        job.rejected_count = rejected_count
        job.row_errors = [item.model_dump() for item in errors] or None
        job.created_question_ids = [item.id for item in accepted_questions]
        job.created_topic_ids = sorted(created_topic_ids) if created_topic_ids else None
        self.repository.save_import_job(job)

        return BulkImportResult(
            job=QuestionImportJobRead.model_validate(job),
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            errors=errors,
            created_question_ids=[item.id for item in accepted_questions],
            created_topic_ids=sorted(created_topic_ids),
            created_assessment_id=created_assessment_id,
        )

    def bulk_import_from_json(self, *, payload: BulkQuestionImportRequest, user_id: int) -> BulkImportResult:
        if len(payload.rows) > settings.BULK_IMPORT_MAX_ROWS:
            raise bad_request(
                f"Row limit exceeded. Maximum allowed is {settings.BULK_IMPORT_MAX_ROWS}",
                error_code="ROW_LIMIT_EXCEEDED",
            )
        return self._run_bulk_import(
            payload=payload,
            user_id=user_id,
            source_type="json",
            file_name=None,
        )

    def bulk_import_from_file(
        self,
        *,
        file_name: str,
        content: bytes,
        user_id: int,
        import_mode: str,
        default_course_id: int | None,
        default_assessment_id: int | None,
        default_academic_session_id: int | None,
        default_semester_id: int | None,
        default_assessment_type: str | None,
        default_question_format: str | None,
        default_duration_minutes: int,
        default_source_type: str,
        auto_categorize_topics: bool,
        draft_theory_without_solution: bool,
    ) -> BulkImportResult:
        parsed_rows, parse_errors, source_type = self._parse_rows_from_file(
            file_name=file_name,
            content=content,
            import_mode=import_mode,
        )
        payload = BulkQuestionImportRequest(
            rows=parsed_rows,
            import_mode=import_mode,
            default_course_id=default_course_id,
            default_assessment_id=default_assessment_id,
            default_academic_session_id=default_academic_session_id,
            default_semester_id=default_semester_id,
            default_assessment_type=default_assessment_type,
            default_question_format=default_question_format,
            default_duration_minutes=default_duration_minutes,
            default_source_type=default_source_type,
            auto_categorize_topics=auto_categorize_topics,
            draft_theory_without_solution=draft_theory_without_solution,
        )
        return self._run_bulk_import(
            payload=payload,
            user_id=user_id,
            source_type=source_type,
            file_name=file_name,
            parse_errors=parse_errors,
        )

    def get_import_job(self, *, job_id: int, user_id: int) -> QuestionImportJob:
        job = self.repository.get_import_job(job_id)
        if job is None or job.created_by_user_id != user_id:
            raise not_found("import_job", job_id)
        return job

    def list_import_jobs(self, *, user_id: int, skip: int, limit: int) -> list[QuestionImportJob]:
        return self.repository.list_import_jobs(user_id=user_id, skip=skip, limit=limit)
