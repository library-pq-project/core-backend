from fastapi import HTTPException, status

from src.modules.courses.models import Course
from src.modules.courses.repository import CourseRepository


class CourseService:
    def __init__(self, repository: CourseRepository):
        self.repository = repository

    def list_courses(self) -> list[Course]:
        return self.repository.list()

    def get_course(self, course_id: int) -> Course:
        course = self.repository.get(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        return course
