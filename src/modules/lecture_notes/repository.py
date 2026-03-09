from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.lecture_notes.models import LectureNote


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
