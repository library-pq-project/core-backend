from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from src.modules.questions.models import Question


class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        *,
        course_id: int | None,
        topic_id: int | None,
        year: int | None,
        question_type: str | None,
        source_type: str | None,
    ) -> list[Question]:
        stmt: Select[tuple[Question]] = select(Question).options(selectinload(Question.options))

        if course_id is not None:
            stmt = stmt.where(Question.course_id == course_id)
        if topic_id is not None:
            stmt = stmt.where(Question.topic_id == topic_id)
        if year is not None:
            stmt = stmt.where(Question.year == year)
        if question_type is not None:
            stmt = stmt.where(Question.question_type == question_type)
        if source_type is not None:
            stmt = stmt.where(Question.source_type == source_type)

        stmt = stmt.order_by(Question.created_at.desc())
        return list(self.db.scalars(stmt))

    def get(self, question_id: int) -> Question | None:
        stmt = select(Question).options(selectinload(Question.options)).where(Question.id == question_id)
        return self.db.scalar(stmt)
