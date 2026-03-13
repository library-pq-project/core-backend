from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.modules.quizzes.models import Quiz, QuizAttempt, QuizQuestion, QuizResponse


class GradingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_quiz_for_grading(self, quiz_id: int, user_id: int) -> Quiz | None:
        stmt = (
            select(Quiz)
            .options(
                selectinload(Quiz.quiz_questions).selectinload(QuizQuestion.options),
                selectinload(Quiz.quiz_questions).selectinload(QuizQuestion.question),
            )
            .where(Quiz.id == quiz_id, Quiz.user_id == user_id)
        )
        return self.db.scalar(stmt)

    def get_attempt(self, quiz_id: int, attempt_id: int, user_id: int) -> QuizAttempt | None:
        stmt = select(QuizAttempt).where(
            QuizAttempt.id == attempt_id,
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def list_attempt_responses(self, attempt_id: int, user_id: int) -> list[QuizResponse]:
        stmt = select(QuizResponse).where(QuizResponse.attempt_id == attempt_id, QuizResponse.user_id == user_id)
        return list(self.db.scalars(stmt))

    def commit(self) -> None:
        self.db.commit()
