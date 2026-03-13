from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.modules.academic.models import Assessment
from src.modules.questions.models import Question
from src.modules.quizzes.models import Quiz, QuizAttempt, QuizQuestion, QuizResponse, QuizResult


class QuizRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_user_quizzes(self, user_id: int, *, skip: int, limit: int) -> list[Quiz]:
        stmt = select(Quiz).where(Quiz.user_id == user_id).order_by(Quiz.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def get_user_quiz(self, quiz_id: int, user_id: int) -> Quiz | None:
        stmt = (
            select(Quiz)
            .options(
                selectinload(Quiz.attempts),
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

    def get_attempt_by_id(self, attempt_id: int, user_id: int) -> QuizAttempt | None:
        stmt = select(QuizAttempt).where(QuizAttempt.id == attempt_id, QuizAttempt.user_id == user_id)
        return self.db.scalar(stmt)

    def get_latest_attempt(self, quiz_id: int, user_id: int) -> QuizAttempt | None:
        stmt = (
            select(QuizAttempt)
            .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.attempt_number.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def select_questions(
        self,
        *,
        course_id: int,
        assessment_id: int | None,
        topic_id: int | None,
        question_source_mode: str,
        question_type_mode: str | None,
        total_questions: int,
    ) -> list[Question]:
        stmt = select(Question).options(selectinload(Question.options)).where(Question.course_id == course_id)
        if assessment_id is not None:
            stmt = stmt.where(Question.assessment_id == assessment_id)

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

    def save_attempt(self, attempt: QuizAttempt) -> QuizAttempt:
        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt

    def get_assessment(self, assessment_id: int) -> Assessment | None:
        return self.db.get(Assessment, assessment_id)

    def upsert_response(self, response: QuizResponse) -> QuizResponse:
        self.db.add(response)
        self.db.commit()
        self.db.refresh(response)
        return response

    def find_response(self, *, attempt_id: int, quiz_question_id: int, user_id: int) -> QuizResponse | None:
        stmt = select(QuizResponse).where(
            QuizResponse.attempt_id == attempt_id,
            QuizResponse.quiz_question_id == quiz_question_id,
            QuizResponse.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def list_responses_for_attempt(self, attempt_id: int, user_id: int) -> list[QuizResponse]:
        stmt = select(QuizResponse).where(QuizResponse.attempt_id == attempt_id, QuizResponse.user_id == user_id)
        return list(self.db.scalars(stmt))

    def save_result(self, result: QuizResult) -> QuizResult:
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def get_result(self, quiz_id: int, user_id: int, attempt_id: int | None = None) -> QuizResult | None:
        stmt = select(QuizResult).where(QuizResult.quiz_id == quiz_id, QuizResult.user_id == user_id)
        if attempt_id is not None:
            stmt = stmt.where(QuizResult.attempt_id == attempt_id)
        else:
            stmt = stmt.order_by(QuizResult.created_at.desc()).limit(1)
        return self.db.scalar(stmt)

    def commit(self) -> None:
        self.db.commit()
