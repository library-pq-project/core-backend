from src.common.enums import GenerationStatus, QuestionSourceType
from src.common.utils import make_fingerprint
from src.modules.ai_generation.providers import AIQuestionGenerator
from src.modules.ai_generation.models import AIQuestionGenerationRequest
from src.modules.ai_generation.repository import AIQuestionGenerationRepository
from src.modules.ai_generation.schemas import AIQuestionGenerationCreate
from src.modules.lecture_notes.repository import LectureNoteRepository
from src.modules.questions.models import Question, QuestionOption


class AIQuestionGenerationService:
    def __init__(
        self,
        repository: AIQuestionGenerationRepository,
        lecture_note_repository: LectureNoteRepository,
        ai_client: AIQuestionGenerator,
    ):
        self.repository = repository
        self.lecture_note_repository = lecture_note_repository
        self.ai_client = ai_client

    def _build_fingerprint(self, payload: AIQuestionGenerationCreate, user_id: int) -> str:
        parts = [
            str(user_id),
            str(payload.assessment_id or "none"),
            str(payload.course_id),
            str(payload.topic_id or "none"),
            str(payload.lecture_note_id or "none"),
            payload.question_type,
            str(payload.requested_count),
        ]
        return make_fingerprint(parts)

    def _get_context_text(self, payload: AIQuestionGenerationCreate, user_id: int) -> str:
        if payload.lecture_note_id is None:
            return "No lecture note attached. Generate generic course questions."

        note = self.lecture_note_repository.get_for_user(payload.lecture_note_id, user_id)
        if not note:
            return "Lecture note not found. Generate generic questions."

        return note.extracted_text or f"Lecture note title: {note.title}"

    def generate_or_reuse(self, payload: AIQuestionGenerationCreate, user_id: int):
        fingerprint = self._build_fingerprint(payload, user_id)
        request = AIQuestionGenerationRequest(
            user_id=user_id,
            assessment_id=payload.assessment_id,
            course_id=payload.course_id,
            topic_id=payload.topic_id,
            lecture_note_id=payload.lecture_note_id,
            question_type=payload.question_type,
            requested_count=payload.requested_count,
            fingerprint=fingerprint,
            status=GenerationStatus.PENDING.value,
        )
        self.repository.create_request(request)

        existing_questions = self.repository.list_ai_questions_by_fingerprint(
            fingerprint, payload.requested_count
        )
        if len(existing_questions) >= payload.requested_count:
            self.repository.mark_request(request, GenerationStatus.COMPLETED)
            return fingerprint, existing_questions, len(existing_questions), 0

        context_text = self._get_context_text(payload, user_id)
        generated_payloads = self.ai_client.generate_questions(
            context_text=context_text,
            question_type=payload.question_type,
            requested_count=payload.requested_count - len(existing_questions),
        )

        created_questions: list[Question] = []
        for generated in generated_payloads:
            question = Question(
                assessment_id=payload.assessment_id,
                course_id=payload.course_id,
                topic_id=payload.topic_id,
                lecture_note_id=payload.lecture_note_id,
                year=None,
                question_text=generated.question_text,
                question_type=payload.question_type,
                source_type=QuestionSourceType.AI_GENERATED.value,
                difficulty_level="medium",
                mark_allocation=1,
                solution_text=generated.solution_text,
                explanation=generated.explanation,
                generation_fingerprint=fingerprint,
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
        return fingerprint, combined, len(existing_questions), len(created_questions)
