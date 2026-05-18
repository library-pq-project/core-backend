from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.courses.models import Course, CourseCompact


class CourseRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, *, skip: int, limit: int) -> list[Course]:
        stmt = select(Course).order_by(Course.code).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def get(self, course_id: int) -> Course | None:
        return self.db.get(Course, course_id)

    def get_by_slug(self, slug: str) -> Course | None:
        return self.db.scalar(select(Course).where(Course.slug == slug))

    def create(self, course: Course) -> Course:
        self.db.add(course)
        self.db.commit()
        self.db.refresh(course)
        return course

    def save(self, course: Course) -> Course:
        self.db.add(course)
        self.db.commit()
        self.db.refresh(course)
        return course

    def delete(self, course: Course) -> None:
        self.db.delete(course)
        self.db.commit()

    def get_active_compact(self, course_id: int) -> CourseCompact | None:
        stmt = (
            select(CourseCompact)
            .where(CourseCompact.course_id == course_id, CourseCompact.is_active.is_(True))
            .order_by(CourseCompact.version.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list_compacts(self, course_id: int, *, active_only: bool, skip: int, limit: int) -> list[CourseCompact]:
        stmt = (
            select(CourseCompact)
            .where(CourseCompact.course_id == course_id)
            .order_by(CourseCompact.version.desc())
        )
        if active_only:
            stmt = stmt.where(CourseCompact.is_active.is_(True))
        stmt = stmt.offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def get_compact_by_slug(self, slug: str) -> CourseCompact | None:
        stmt = select(CourseCompact).where(CourseCompact.slug == slug)
        return self.db.scalar(stmt)

    def get_compact(self, compact_id: int) -> CourseCompact | None:
        return self.db.get(CourseCompact, compact_id)

    def create_compact(self, compact: CourseCompact) -> CourseCompact:
        self.db.add(compact)
        self.db.commit()
        self.db.refresh(compact)
        return compact

    def deactivate_compacts(self, course_id: int) -> None:
        stmt = select(CourseCompact).where(CourseCompact.course_id == course_id, CourseCompact.is_active.is_(True))
        for item in self.db.scalars(stmt):
            item.is_active = False
        self.db.flush()

    def get_next_compact_version(self, course_id: int) -> int:
        stmt = select(CourseCompact).where(CourseCompact.course_id == course_id).order_by(CourseCompact.version.desc()).limit(1)
        latest = self.db.scalar(stmt)
        if latest is None:
            return 1
        return latest.version + 1
