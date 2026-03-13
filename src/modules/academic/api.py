from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.academic.repository import AcademicRepository
from src.modules.academic.schemas import (
    AcademicSessionCreate,
    AcademicSessionRead,
    ActiveCalendarRead,
    ActiveCalendarUpdate,
    AssessmentCreate,
    AssessmentRead,
    ProgramCourseOfferingCreate,
    ProgramCourseOfferingRead,
    ProgramCreate,
    ProgramRead,
    SemesterCreate,
    SemesterRead,
)
from src.modules.academic.service import AcademicService
from src.modules.auth.api import get_current_user, require_admin
from src.modules.auth.models import User
from src.modules.courses.schemas import CourseRead

router = APIRouter()


def get_academic_service(db: Session = Depends(get_db)) -> AcademicService:
    return AcademicService(AcademicRepository(db))


@router.post("/sessions", response_model=AcademicSessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(payload: AcademicSessionCreate, service: AcademicService = Depends(get_academic_service), _=Depends(require_admin)):
    return service.create_session(payload)


@router.get("/sessions", response_model=list[AcademicSessionRead])
async def list_sessions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: AcademicService = Depends(get_academic_service),
):
    return service.list_sessions(skip=skip, limit=limit)


@router.post("/semesters", response_model=SemesterRead, status_code=status.HTTP_201_CREATED)
async def create_semester(payload: SemesterCreate, service: AcademicService = Depends(get_academic_service), _=Depends(require_admin)):
    return service.create_semester(payload)


@router.get("/semesters", response_model=list[SemesterRead])
async def list_semesters(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: AcademicService = Depends(get_academic_service),
):
    return service.list_semesters(skip=skip, limit=limit)


@router.post("/programs", response_model=ProgramRead, status_code=status.HTTP_201_CREATED)
async def create_program(payload: ProgramCreate, service: AcademicService = Depends(get_academic_service), _=Depends(require_admin)):
    return service.create_program(payload)


@router.get("/programs", response_model=list[ProgramRead])
async def list_programs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: AcademicService = Depends(get_academic_service),
):
    return service.list_programs(skip=skip, limit=limit)


@router.put("/active-calendar", response_model=ActiveCalendarRead)
async def set_active_calendar(
    payload: ActiveCalendarUpdate,
    service: AcademicService = Depends(get_academic_service),
    _=Depends(require_admin),
):
    return service.set_active_calendar(payload)


@router.get("/active-calendar", response_model=ActiveCalendarRead)
async def get_active_calendar(service: AcademicService = Depends(get_academic_service)):
    return service.get_active_calendar()


@router.get("/me/offered-courses", response_model=list[CourseRead])
async def get_my_offered_courses(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: AcademicService = Depends(get_academic_service),
):
    return service.list_student_offered_courses(student=current_user, skip=skip, limit=limit)


@router.post("/offerings", response_model=ProgramCourseOfferingRead, status_code=status.HTTP_201_CREATED)
async def create_program_offering(
    payload: ProgramCourseOfferingCreate,
    service: AcademicService = Depends(get_academic_service),
    _=Depends(require_admin),
):
    return service.create_offering(payload)


@router.get("/offerings", response_model=list[ProgramCourseOfferingRead])
async def list_program_offerings(
    program_id: int | None = Query(default=None),
    academic_session_id: int | None = Query(default=None),
    semester_id: int | None = Query(default=None),
    level: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: AcademicService = Depends(get_academic_service),
):
    return service.list_offerings(
        program_id=program_id,
        academic_session_id=academic_session_id,
        semester_id=semester_id,
        level=level,
        skip=skip,
        limit=limit,
    )


@router.post("/assessments", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    payload: AssessmentCreate,
    service: AcademicService = Depends(get_academic_service),
    _=Depends(require_admin),
):
    return service.create_assessment(payload)


@router.get("/assessments", response_model=list[AssessmentRead])
async def list_assessments(
    course_id: int | None = Query(default=None),
    academic_session_id: int | None = Query(default=None),
    semester_id: int | None = Query(default=None),
    assessment_type: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: AcademicService = Depends(get_academic_service),
):
    return service.list_assessments(
        course_id=course_id,
        academic_session_id=academic_session_id,
        semester_id=semester_id,
        assessment_type=assessment_type,
        skip=skip,
        limit=limit,
    )
