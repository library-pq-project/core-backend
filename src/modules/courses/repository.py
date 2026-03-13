from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.courses.models import Course


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
