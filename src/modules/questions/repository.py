from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from src.modules.academic.models import Assessment
from src.modules.courses.models import Course
from src.modules.lecture_notes.models import LectureNote
from src.modules.questions.models import Question, QuestionImportJob


class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(
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
        stmt: Select[tuple[Question]] = select(Question).options(selectinload(Question.options))

        if assessment_id is not None:
            stmt = stmt.where(Question.assessment_id == assessment_id)
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

        stmt = stmt.order_by(Question.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def get(self, question_id: int) -> Question | None:
        stmt = select(Question).options(selectinload(Question.options)).where(Question.id == question_id)
        return self.db.scalar(stmt)

    def get_assessment(self, assessment_id: int) -> Assessment | None:
        return self.db.get(Assessment, assessment_id)

    def get_course(self, course_id: int) -> Course | None:
        return self.db.get(Course, course_id)

    def get_lecture_note(self, lecture_note_id: int) -> LectureNote | None:
        return self.db.get(LectureNote, lecture_note_id)

    def create(self, question: Question) -> Question:
        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)
        return question

    def create_many(self, questions: list[Question]) -> list[Question]:
        self.db.add_all(questions)
        self.db.commit()
        for question in questions:
            self.db.refresh(question)
        return questions

    def save(self, question: Question) -> Question:
        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)
        return question

    def delete(self, question: Question) -> None:
        self.db.delete(question)
        self.db.commit()

    def create_import_job(self, job: QuestionImportJob) -> QuestionImportJob:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def save_import_job(self, job: QuestionImportJob) -> QuestionImportJob:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_import_job(self, job_id: int) -> QuestionImportJob | None:
        return self.db.get(QuestionImportJob, job_id)

    def list_import_jobs(self, *, user_id: int, skip: int, limit: int) -> list[QuestionImportJob]:
        stmt = (
            select(QuestionImportJob)
            .where(QuestionImportJob.created_by_user_id == user_id)
            .order_by(QuestionImportJob.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt))
