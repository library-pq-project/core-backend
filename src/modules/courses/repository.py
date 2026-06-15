from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.modules.academic.models import ProgramCourseOffering, Semester
from src.modules.courses.models import Course, CourseCompact


class CourseRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        *,
        skip: int,
        limit: int,
        semester_id: int | None = None,
        level: str | None = None,
        program_id: int | None = None,
        academic_session_id: int | None = None,
        code: str | None = None,
        search: str | None = None,
    ) -> list[Course]:
        stmt = select(Course)
        join_offerings = any(value is not None for value in (program_id, academic_session_id))

        if join_offerings:
            stmt = stmt.join(ProgramCourseOffering, ProgramCourseOffering.course_id == Course.id)
            stmt = stmt.distinct()
            if program_id is not None:
                stmt = stmt.where(ProgramCourseOffering.program_id == program_id)
            if academic_session_id is not None:
                stmt = stmt.where(ProgramCourseOffering.academic_session_id == academic_session_id)

        if level is not None:
            if join_offerings:
                stmt = stmt.where(or_(Course.level == level, ProgramCourseOffering.level == level))
            else:
                stmt = stmt.where(Course.level == level)

        if semester_id is not None:
            if join_offerings:
                stmt = stmt.where(
                    or_(
                        Course.semester_id == semester_id,
                        ProgramCourseOffering.semester_id == semester_id,
                    )
                )
            else:
                stmt = stmt.where(Course.semester_id == semester_id)

        if code is not None:
            stmt = stmt.where(Course.code == code)

        if search is not None:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Course.code.ilike(term),
                    Course.title.ilike(term),
                    Course.description.ilike(term),
                )
            )

        stmt = stmt.order_by(Course.code).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def get(self, course_id: int) -> Course | None:
        return self.db.get(Course, course_id)

    def get_by_slug(self, slug: str) -> Course | None:
        return self.db.scalar(select(Course).where(Course.slug == slug))

    def get_semester(self, semester_id: int) -> Semester | None:
        return self.db.get(Semester, semester_id)

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
