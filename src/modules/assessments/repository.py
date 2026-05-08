from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.modules.academic.models import Assessment
from src.modules.questions.models import Question
from src.modules.topics.models import Topic


class AssessmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, assessment: Assessment) -> Assessment:
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        return assessment

    def list(
        self,
        *,
        course_id: int | None,
        academic_session_id: int | None,
        semester_id: int | None,
        assessment_type: str | None,
        source_type: str | None,
        created_by_user_id: int | None,
        skip: int,
        limit: int,
    ) -> list[Assessment]:
        stmt = select(Assessment)
        if course_id is not None:
            stmt = stmt.where(Assessment.course_id == course_id)
        if academic_session_id is not None:
            stmt = stmt.where(Assessment.academic_session_id == academic_session_id)
        if semester_id is not None:
            stmt = stmt.where(Assessment.semester_id == semester_id)
        if assessment_type is not None:
            stmt = stmt.where(Assessment.assessment_type == assessment_type)
        if source_type is not None:
            stmt = stmt.where(Assessment.source_type == source_type)
        if created_by_user_id is not None:
            stmt = stmt.where(Assessment.created_by_user_id == created_by_user_id)
        stmt = stmt.order_by(Assessment.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def get(self, assessment_id: int) -> Assessment | None:
        return self.db.get(Assessment, assessment_id)

    def list_questions(
        self,
        *,
        assessment_id: int,
        question_type: str | None,
        source_type: str | None,
        skip: int,
        limit: int,
    ) -> list[Question]:
        stmt = (
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.assessment_id == assessment_id)
            .order_by(Question.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if question_type is not None:
            stmt = stmt.where(Question.question_type == question_type)
        if source_type is not None:
            stmt = stmt.where(Question.source_type == source_type)
        return list(self.db.scalars(stmt))

    def list_with_counts(
        self,
        *,
        course_id: int | None,
        academic_session_id: int | None,
        semester_id: int | None,
        assessment_type: str | None,
        source_type: str | None,
        created_by_user_id: int | None,
        skip: int,
        limit: int,
    ) -> list[tuple[Assessment, int]]:
        stmt = (
            select(Assessment, func.count(Question.id))
            .outerjoin(Question, Question.assessment_id == Assessment.id)
            .group_by(Assessment.id)
        )
        if course_id is not None:
            stmt = stmt.where(Assessment.course_id == course_id)
        if academic_session_id is not None:
            stmt = stmt.where(Assessment.academic_session_id == academic_session_id)
        if semester_id is not None:
            stmt = stmt.where(Assessment.semester_id == semester_id)
        if assessment_type is not None:
            stmt = stmt.where(Assessment.assessment_type == assessment_type)
        if source_type is not None:
            stmt = stmt.where(Assessment.source_type == source_type)
        if created_by_user_id is not None:
            stmt = stmt.where(Assessment.created_by_user_id == created_by_user_id)
        stmt = stmt.order_by(Assessment.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.execute(stmt).all())

    def count_questions(
        self,
        *,
        assessment_id: int,
        topic_ids: list[int] | None = None,
    ) -> int:
        stmt = select(func.count(Question.id)).where(
            Question.assessment_id == assessment_id,
            Question.is_active.is_(True),
        )
        if topic_ids:
            stmt = stmt.where(Question.topic_id.in_(topic_ids))
        return int(self.db.scalar(stmt) or 0)

    def list_topics_for_assessment(self, assessment_id: int) -> list[Topic]:
        stmt = (
            select(Topic)
            .join(Question, Question.topic_id == Topic.id)
            .where(Question.assessment_id == assessment_id)
            .distinct()
            .order_by(Topic.name.asc())
        )
        return list(self.db.scalars(stmt))
