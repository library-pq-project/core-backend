from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.courses.models import Course, CourseCompact
from src.modules.lecture_notes.models import LectureNote
from src.modules.topics.models import Topic


class LectureNoteRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, lecture_note: LectureNote) -> LectureNote:
        self.db.add(lecture_note)
        self.db.commit()
        self.db.refresh(lecture_note)
        return lecture_note

    def list_by_user(self, user_id: int, *, skip: int, limit: int) -> list[LectureNote]:
        stmt = select(LectureNote).where(LectureNote.user_id == user_id).order_by(LectureNote.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def get_for_user(self, lecture_note_id: int, user_id: int) -> LectureNote | None:
        stmt = select(LectureNote).where(
            LectureNote.id == lecture_note_id, LectureNote.user_id == user_id
        )
        return self.db.scalar(stmt)

    def delete(self, lecture_note: LectureNote) -> None:
        self.db.delete(lecture_note)
        self.db.commit()

    def get_course_relevance_context(self, course_id: int) -> dict:
        course = self.db.get(Course, course_id)
        if course is None:
            return {"course": None, "topics": [], "compact": None}

        topics = list(
            self.db.scalars(
                select(Topic).where(Topic.course_id == course_id).order_by(Topic.name.asc())
            )
        )
        compact = self.db.scalar(
            select(CourseCompact)
            .where(CourseCompact.course_id == course_id, CourseCompact.is_active.is_(True))
            .order_by(CourseCompact.version.desc())
            .limit(1)
        )
        return {"course": course, "topics": topics, "compact": compact}
