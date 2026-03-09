from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.modules.questions.models import Question
from src.modules.quizzes.models import Quiz, QuizQuestion, QuizResponse, QuizResult


class QuizRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_user_quizzes(self, user_id: int, *, skip: int, limit: int) -> list[Quiz]:
        stmt = select(Quiz).where(Quiz.user_id == user_id).order_by(Quiz.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def get_user_quiz(self, quiz_id: int, user_id: int) -> Quiz | None:
        stmt = (
            select(Quiz)
            .options(
                selectinload(Quiz.quiz_questions).selectinload(QuizQuestion.options),
                selectinload(Quiz.quiz_questions).selectinload(QuizQuestion.question),
            )
            .where(Quiz.id == quiz_id, Quiz.user_id == user_id)
        )
        return self.db.scalar(stmt)

    def select_questions(
        self,
        *,
        course_id: int,
        topic_id: int | None,
        question_source_mode: str,
        question_type_mode: str | None,
        total_questions: int,
    ) -> list[Question]:
        stmt = select(Question).options(selectinload(Question.options)).where(Question.course_id == course_id)

        if topic_id is not None:
            stmt = stmt.where(Question.topic_id == topic_id)

        if question_source_mode == "actual_only":
            stmt = stmt.where(Question.source_type == "actual")
        elif question_source_mode == "ai_only":
            stmt = stmt.where(Question.source_type == "ai_generated")

        if question_type_mode:
            stmt = stmt.where(Question.question_type == question_type_mode)

        stmt = stmt.where(Question.is_active.is_(True)).order_by(func.random()).limit(total_questions)
        return list(self.db.scalars(stmt))

    def save_quiz(self, quiz: Quiz) -> Quiz:
        self.db.add(quiz)
        self.db.commit()
        self.db.refresh(quiz)
        return quiz

    def upsert_response(self, response: QuizResponse) -> QuizResponse:
        self.db.add(response)
        self.db.commit()
        self.db.refresh(response)
        return response

    def find_response(self, quiz_question_id: int, user_id: int) -> QuizResponse | None:
        stmt = select(QuizResponse).where(
            QuizResponse.quiz_question_id == quiz_question_id,
            QuizResponse.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def list_responses_for_quiz(self, quiz_id: int, user_id: int) -> list[QuizResponse]:
        stmt = (
            select(QuizResponse)
            .join(QuizQuestion, QuizQuestion.id == QuizResponse.quiz_question_id)
            .where(QuizQuestion.quiz_id == quiz_id, QuizResponse.user_id == user_id)
        )
        return list(self.db.scalars(stmt))

    def save_result(self, result: QuizResult) -> QuizResult:
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def get_result(self, quiz_id: int, user_id: int) -> QuizResult | None:
        stmt = select(QuizResult).where(QuizResult.quiz_id == quiz_id, QuizResult.user_id == user_id)
        return self.db.scalar(stmt)

    def commit(self) -> None:
        self.db.commit()
