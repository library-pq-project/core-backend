from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.modules.quizzes.models import Quiz, QuizQuestion, QuizResponse


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

    def list_responses(self, quiz_id: int, user_id: int) -> list[QuizResponse]:
        stmt = (
            select(QuizResponse)
            .join(QuizQuestion, QuizQuestion.id == QuizResponse.quiz_question_id)
            .where(QuizQuestion.quiz_id == quiz_id, QuizResponse.user_id == user_id)
        )
        return list(self.db.scalars(stmt))

    def commit(self) -> None:
        self.db.commit()
