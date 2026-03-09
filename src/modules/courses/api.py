from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.courses.repository import CourseRepository
from src.modules.courses.schemas import CourseRead
from src.modules.courses.service import CourseService

router = APIRouter()


def get_course_service(db: Session = Depends(get_db)) -> CourseService:
    return CourseService(CourseRepository(db))


@router.get("", response_model=list[CourseRead])
async def list_courses(service: CourseService = Depends(get_course_service)):
    return service.list_courses()


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(course_id: int, service: CourseService = Depends(get_course_service)):
    return service.get_course(course_id)
