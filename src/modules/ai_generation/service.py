from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select

from src.common.enums import GenerationStatus, QuestionSourceType
from src.common.utils import generate_slug, make_fingerprint
from src.core.config import settings
from src.core.prototype import ensure_prototype_course, ensure_prototype_topic
from src.modules.academic.models import AcademicCalendarState, Assessment
from src.modules.ai_generation.providers import AIQuestionGenerator
from src.modules.ai_generation.models import AIQuestionGenerationRequest
from src.modules.ai_generation.repository import AIQuestionGenerationRepository
from src.modules.ai_generation.schemas import AIQuestionGenerationCreate
from src.modules.courses.repository import CourseRepository
from src.modules.lecture_notes.repository import LectureNoteRepository
from src.modules.questions.models import Question, QuestionOption
from src.modules.topics.categorization import TopicCategorizationService
from src.modules.topics.repository import TopicRepository


class AIQuestionGenerationService:
    def __init__(
        self,
        repository: AIQuestionGenerationRepository,
        lecture_note_repository: LectureNoteRepository,
        course_repository: CourseRepository,
        topic_repository: TopicRepository,
        ai_client: AIQuestionGenerator,
    ):
        self.repository = repository
        self.lecture_note_repository = lecture_note_repository
        self.course_repository = course_repository
        self.topic_repository = topic_repository
        self.ai_client = ai_client
        self.topic_categorizer = TopicCategorizationService(topic_repository)

    def _build_fingerprint(self, payload: AIQuestionGenerationCreate, user_id: int) -> str:
        normalized_topic_ids = self._normalize_topic_ids(payload.topic_ids)
        parts = [
            str(user_id),
            str(payload.course_id),
            str(payload.lecture_note_id or "none"),
            payload.question_type,
            payload.difficulty_level,
            payload.quiz_title,
            payload.user_prompt,
            str(payload.requested_count),
            ",".join(str(item) for item in (normalized_topic_ids or [])),
        ]
        return make_fingerprint(parts)

    def _normalize_topic_ids(self, topic_ids: list[int] | None) -> list[int] | None:
        if not topic_ids:
            return None
        cleaned = sorted({topic_id for topic_id in topic_ids if topic_id and topic_id > 0})
        return cleaned or None

    def _create_generated_assessment(
        self,
        *,
        user_id: int,
        course_id: int,
        quiz_title: str,
        question_type: str,
    ) -> Assessment:
        active_calendar = self.repository.db.scalar(
            select(AcademicCalendarState).order_by(AcademicCalendarState.id.asc())
        )
        if active_calendar is None:
            if settings.PROTOTYPE_MODE:
                from src.core.prototype import ensure_prototype_user_with_prerequisites

                ensure_prototype_user_with_prerequisites(
                    self.repository.db,
                    user_id=settings.PROTOTYPE_USER_ID,
                    role=settings.PROTOTYPE_USER_ROLE,
                )
                active_calendar = self.repository.db.scalar(
                    select(AcademicCalendarState).order_by(AcademicCalendarState.id.asc())
                )
        if active_calendar is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active academic calendar is required to generate assessment-linked AI questions.",
            )

        now_tag = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        slug = generate_slug(f"ai-{quiz_title}-{user_id}-{now_tag}")
        assessment = Assessment(
            course_id=course_id,
            academic_session_id=active_calendar.academic_session_id,
            semester_id=active_calendar.semester_id,
            assessment_type="AI Practice Set",
            question_format=question_type,
            default_duration_minutes=60,
            year_label=str(now_tag[:4]),
            source_type=QuestionSourceType.AI_GENERATED.value,
            created_by_user_id=user_id,
            slug=slug,
        )
        self.repository.db.add(assessment)
        self.repository.db.flush()
        return assessment

    def _get_context_text(self, payload: AIQuestionGenerationCreate, user_id: int) -> str:
        course = self.course_repository.get(payload.course_id)
        if course is None and settings.PROTOTYPE_MODE:
            course = ensure_prototype_course(self.repository.db, course_id=payload.course_id)
        if course is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        context_blocks: list[str] = [
            f"Course code: {course.code}",
            f"Course title: {course.title}",
            f"Course description: {course.description or ''}",
        ]
        compact = self.course_repository.get_active_compact(payload.course_id)
        if compact:
            context_blocks.append(f"Active compact version: {compact.version}")
            context_blocks.append(f"Compact summary: {compact.compact_summary or ''}")
            context_blocks.append(f"Compact taxonomy: {compact.taxonomy_text or ''}")
            context_blocks.append(f"Common pitfalls: {compact.pitfalls_text or ''}")

        selected_topics = []
        normalized_topic_ids = self._normalize_topic_ids(payload.topic_ids)
        if normalized_topic_ids:
            selected_topics = [
                topic
                for topic in (self.topic_repository.get(topic_id) for topic_id in normalized_topic_ids)
                if topic and topic.course_id == payload.course_id
            ]

        if selected_topics:
            context_blocks.append(
                "Selected topics: " + "; ".join(f"{item.name} ({item.description or ''})" for item in selected_topics)
            )
        else:
            course_topics = self.topic_repository.list(course_id=payload.course_id, skip=0, limit=200)
            context_blocks.append(
                "Course topics: " + "; ".join(f"{item.name} ({item.description or ''})" for item in course_topics)
            )

        if payload.lecture_note_id is not None:
            note = self.lecture_note_repository.get_for_user(payload.lecture_note_id, user_id)
            if note is None:
                if settings.PROTOTYPE_MODE:
                    context_blocks.append("Lecture note not found in prototype mode; continuing with course context only.")
                    note = None
                else:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecture note not found")
            if note is not None and note.course_id != payload.course_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="lecture_note_id does not belong to selected course_id",
                )
            if note is not None:
                context_blocks.append(f"Lecture note title: {note.title}")
                context_blocks.append(f"Lecture note excerpt: {(note.extracted_text or '')[:6000]}")

        context_blocks.append(f"User prompt: {payload.user_prompt}")
        context_blocks.append(f"Target question type: {payload.question_type}")
        context_blocks.append(f"Target difficulty: {payload.difficulty_level}")
        return "\n".join(context_blocks)

    def generate_or_reuse(self, payload: AIQuestionGenerationCreate, user_id: int):
        normalized_topic_ids = self._normalize_topic_ids(payload.topic_ids)
        if settings.PROTOTYPE_MODE:
            ensure_prototype_course(self.repository.db, course_id=payload.course_id)
            for topic_id in normalized_topic_ids or []:
                ensure_prototype_topic(self.repository.db, course_id=payload.course_id, topic_id=topic_id)

        generated_assessment = self._create_generated_assessment(
            user_id=user_id,
            course_id=payload.course_id,
            quiz_title=payload.quiz_title,
            question_type=payload.question_type,
        )

        fingerprint = self._build_fingerprint(payload, user_id)
        request = AIQuestionGenerationRequest(
            user_id=user_id,
            assessment_id=generated_assessment.id,
            course_id=payload.course_id,
            topic_id=(normalized_topic_ids[0] if normalized_topic_ids else None),
            lecture_note_id=payload.lecture_note_id,
            question_type=payload.question_type,
            quiz_title=payload.quiz_title,
            user_prompt=payload.user_prompt,
            exam_type=payload.question_type,
            difficulty_level=payload.difficulty_level,
            requested_count=payload.requested_count,
            fingerprint=fingerprint,
            status=GenerationStatus.PENDING.value,
        )
        self.repository.create_request(request)
        try:
            existing_questions = self.repository.list_ai_questions_by_fingerprint(
                fingerprint, payload.requested_count
            )
            if len(existing_questions) >= payload.requested_count:
                request.model_name = getattr(self.ai_client, "model", "gemini-3.1-pro-preview")
                request.estimated_input_tokens = 0
                request.estimated_output_tokens = max(1, sum(len(item.question_text or "") for item in existing_questions) // 4)
                self.repository.mark_request(request, GenerationStatus.COMPLETED)
                return (
                    fingerprint,
                    existing_questions,
                    len(existing_questions),
                    0,
                    request.model_name,
                    request.estimated_input_tokens,
                    request.estimated_output_tokens,
                )

            context_text = self._get_context_text(payload, user_id)
            generated_payloads, telemetry = self.ai_client.generate_questions(
                context_text=context_text,
                question_type=payload.question_type,
                difficulty_level=payload.difficulty_level,
                user_prompt=payload.user_prompt,
                requested_count=payload.requested_count - len(existing_questions),
            )
            request.model_name = telemetry.model_name
            request.estimated_input_tokens = telemetry.estimated_input_tokens
            request.estimated_output_tokens = telemetry.estimated_output_tokens

            created_questions: list[Question] = []
            for generated in generated_payloads:
                allowed_topic_ids = set(normalized_topic_ids or []) or None
                chosen_topic_id, confidence, trace = self.topic_categorizer.classify_question_topic(
                    course_id=payload.course_id,
                    question_text=generated.question_text,
                    allowed_topic_ids=allowed_topic_ids,
                )
                question = Question(
                    assessment_id=generated_assessment.id,
                    course_id=payload.course_id,
                    topic_id=chosen_topic_id,
                    lecture_note_id=payload.lecture_note_id,
                    year=None,
                    question_text=generated.question_text,
                    source_text=generated.question_text,
                    content_format="markdown_latex",
                    question_type=payload.question_type,
                    source_type=QuestionSourceType.AI_GENERATED.value,
                    difficulty_level=payload.difficulty_level if payload.difficulty_level != "mixed" else "medium",
                    mark_allocation=1,
                    marking_scheme="Award full mark for complete correctness and conceptual accuracy.",
                    solution_text=generated.solution_text,
                    explanation=generated.explanation,
                    generation_fingerprint=fingerprint,
                    ai_topic_confidence=confidence,
                    ai_topic_trace=trace,
                    is_active=True,
                )
                question.options = [
                    QuestionOption(
                        option_text=option_text,
                        is_correct=index == generated.correct_index,
                        position=index + 1,
                    )
                    for index, option_text in enumerate(generated.options)
                ]
                created_questions.append(question)

            if created_questions:
                created_questions = self.repository.create_questions(created_questions)

            combined = existing_questions + created_questions
            self.repository.mark_request(request, GenerationStatus.COMPLETED)
            return (
                fingerprint,
                combined,
                len(existing_questions),
                len(created_questions),
                telemetry.model_name,
                telemetry.estimated_input_tokens,
                telemetry.estimated_output_tokens,
            )
        except Exception as exc:
            request.failure_reason = str(exc)[:500]
            self.repository.mark_request(request, GenerationStatus.FAILED)
            raise
