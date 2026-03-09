from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.courses.models import Course


class CourseRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Course]:
        return list(self.db.scalars(select(Course).order_by(Course.code)))

    def get(self, course_id: int) -> Course | None:
        return self.db.get(Course, course_id)
