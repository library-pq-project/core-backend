import csv
import io
import json

from fastapi import HTTPException, status

from src.common.utils import generate_slug
from src.core.config import settings
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        return question

    def create_question(self, payload: QuestionCreate) -> Question:
        if payload.assessment_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="assessment_id is required",
            )
        assessment = self.repository.get_assessment(payload.assessment_id)
        if assessment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found",
            )
        derived_course_id = assessment.course_id
        if payload.course_id is not None and payload.course_id != derived_course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="course_id does not match the selected assessment. Omit course_id or use the assessment's course.",
            )
        source_text = payload.source_text or payload.question_text
        if source_text is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either source_text or question_text is required",
            )
        if payload.topic_id is not None:
            topic = self.topic_repository.get(payload.topic_id)
            if topic is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
            if topic.course_id != derived_course_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected topic does not belong to the assessment's course",
                )
        if payload.lecture_note_id is not None:
            lecture_note = self.repository.get_lecture_note(payload.lecture_note_id)
            if lecture_note is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecture note not found")
            if lecture_note.course_id != derived_course_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected lecture note does not belong to the assessment's course",
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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="assessment_id cannot be removed from an existing question",
                )
            assessment = self.repository.get_assessment(assessment_id)
            if assessment is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
            question.assessment_id = assessment.id
            question.course_id = assessment.course_id
            updates.pop("assessment_id", None)

        if "course_id" in updates:
            requested_course_id = updates.pop("course_id")
            if requested_course_id is not None and requested_course_id != question.course_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="course_id is derived from assessment_id and cannot be changed directly",
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
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
            if topic.course_id != question.course_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected topic does not belong to the question's course",
                )

        if "lecture_note_id" in updates and question.lecture_note_id is not None:
            lecture_note = self.repository.get_lecture_note(question.lecture_note_id)
            if lecture_note is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecture note not found")
            if lecture_note.course_id != question.course_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected lecture note does not belong to the question's course",
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

    def _parse_rows_from_file(self, *, file_name: str, content: bytes) -> tuple[list[BulkQuestionRow], list[ImportRowError], str]:
        extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        raw_rows: list[dict] = []

        if extension == "json":
            source_type = "json"
            loaded = json.loads(content.decode("utf-8"))
            if isinstance(loaded, dict):
                loaded = loaded.get("rows", [])
            if not isinstance(loaded, list):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON upload must contain a list under rows")
            raw_rows = [dict(item) for item in loaded if isinstance(item, dict)]
        elif extension == "csv":
            source_type = "csv"
            text = content.decode("utf-8", errors="ignore")
            raw_rows = [dict(item) for item in csv.DictReader(io.StringIO(text))]
        elif extension == "xlsx":
            source_type = "xlsx"
            try:
                from openpyxl import load_workbook
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="openpyxl is required for xlsx upload") from exc
            workbook = load_workbook(io.BytesIO(content), data_only=True)
            sheet = workbook.active
            rows = list(sheet.iter_rows(values_only=True))
            if rows:
                headers = [str(item).strip() if item is not None else "" for item in rows[0]]
                for values in rows[1:]:
                    row = {}
                    for header, value in zip(headers, values):
                        if header:
                            row[header] = value
                    raw_rows.append(row)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported bulk upload file type")

        if len(raw_rows) > settings.BULK_IMPORT_MAX_ROWS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Row limit exceeded. Maximum allowed is {settings.BULK_IMPORT_MAX_ROWS}",
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
        )

    def bulk_import_from_json(self, *, payload: BulkQuestionImportRequest, user_id: int) -> BulkImportResult:
        if len(payload.rows) > settings.BULK_IMPORT_MAX_ROWS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Row limit exceeded. Maximum allowed is {settings.BULK_IMPORT_MAX_ROWS}",
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
        default_source_type: str,
        auto_categorize_topics: bool,
        draft_theory_without_solution: bool,
    ) -> BulkImportResult:
        parsed_rows, parse_errors, source_type = self._parse_rows_from_file(file_name=file_name, content=content)
        payload = BulkQuestionImportRequest(
            rows=parsed_rows,
            import_mode=import_mode,
            default_course_id=default_course_id,
            default_assessment_id=default_assessment_id,
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
        return job

    def list_import_jobs(self, *, user_id: int, skip: int, limit: int) -> list[QuestionImportJob]:
        return self.repository.list_import_jobs(user_id=user_id, skip=skip, limit=limit)
