from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.common.utils import generate_slug
from src.modules.courses.models import Course
from src.modules.courses.repository import CourseRepository
from src.modules.courses.schemas import CourseCreate, CourseUpdate


class CourseService:
    def __init__(self, repository: CourseRepository):
        self.repository = repository

    def list_courses(self, *, skip: int, limit: int) -> list[Course]:
        return self.repository.list(skip=skip, limit=limit)

    def get_course(self, course_id: int) -> Course:
        course = self.repository.get(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        return course

    def get_course_by_slug(self, course_slug: str) -> Course:
        course = self.repository.get_by_slug(course_slug)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        return course

    def create_course(self, payload: CourseCreate) -> Course:
        course = Course(
            code=payload.code,
            slug=generate_slug(payload.code),
            title=payload.title,
            description=payload.description,
            level=payload.level,
            semester=payload.semester,
        )
        try:
            return self.repository.create(course)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Course with this code or slug already exists",
            ) from exc

    def update_course(self, course_id: int, payload: CourseUpdate) -> Course:
        course = self.get_course(course_id)
        updates = payload.model_dump(exclude_unset=True)

        if "code" in updates:
            course.code = updates["code"]
        if "title" in updates:
            course.slug = generate_slug(updates["title"])
        if "title" in updates:
            course.title = updates["title"]
        if "description" in updates:
            course.description = updates["description"]
        if "level" in updates:
            course.level = updates["level"]
        if "semester" in updates:
            course.semester = updates["semester"]

        try:
            return self.repository.save(course)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Course with this code or slug already exists",
            ) from exc

    def delete_course(self, course_id: int) -> None:
        course = self.get_course(course_id)
        self.repository.delete(course)
