from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.common.enums import GenerationStatus, QuestionSourceType
from src.modules.ai_generation.models import AIQuestionGenerationRequest
from src.modules.questions.models import Question, QuestionOption


class AIQuestionGenerationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_request(self, request: AIQuestionGenerationRequest) -> AIQuestionGenerationRequest:
        self.db.add(request)
        self.db.flush()
        return request

    def list_ai_questions_by_fingerprint(self, fingerprint: str, limit: int) -> list[Question]:
        stmt = (
            select(Question)
            .options(selectinload(Question.options))
            .where(
                Question.generation_fingerprint == fingerprint,
                Question.source_type == QuestionSourceType.AI_GENERATED.value,
                Question.is_active.is_(True),
            )
            .order_by(Question.created_at.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def create_questions(self, questions: list[Question]) -> list[Question]:
        self.db.add_all(questions)
        self.db.flush()
        for question in questions:
            for option in question.options:
                self.db.add(option)
        self.db.commit()
        for question in questions:
            self.db.refresh(question)
        return questions

    def mark_request(self, request: AIQuestionGenerationRequest, status: GenerationStatus) -> None:
        request.status = status.value
        if status == GenerationStatus.COMPLETED:
            from src.common.utils import now_utc

            request.completed_at = now_utc()
        self.db.commit()
