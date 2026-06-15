from fastapi import APIRouter, Depends, Query, Response, status
from fastapi import File, Form, UploadFile
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.auth.api import require_admin
from src.modules.auth.models import User
from src.modules.auth.api import get_current_user
from src.modules.courses.repository import CourseRepository
from src.modules.courses.schemas import CourseCompactRead, CourseCompactUploadRead, CourseCreate, CourseRead, CourseUpdate
from src.modules.courses.service import CourseService
from src.modules.topics.repository import TopicRepository
from src.modules.topics.schemas import TopicBulkUpsertResult

router = APIRouter()


def get_course_service(db: Session = Depends(get_db)) -> CourseService:
    return CourseService(CourseRepository(db), topic_repository=TopicRepository(db))


@router.get("", response_model=list[CourseRead])
async def list_courses(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    semester_id: int | None = Query(default=None, ge=1),
    level: str | None = Query(default=None),
    program_id: int | None = Query(default=None, ge=1),
    academic_session_id: int | None = Query(default=None, ge=1),
    code: str | None = Query(default=None),
    search: str | None = Query(default=None),
    service: CourseService = Depends(get_course_service),
):
    return service.list_courses(
        skip=skip,
        limit=limit,
        semester_id=semester_id,
        level=level,
        program_id=program_id,
        academic_session_id=academic_session_id,
        code=code,
        search=search,
    )


@router.get("/slug/{course_slug}", response_model=CourseRead)
async def get_course_by_slug(course_slug: str, service: CourseService = Depends(get_course_service)):
    return service.get_course_by_slug(course_slug)


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(course_id: int, service: CourseService = Depends(get_course_service)):
    return service.get_course(course_id)


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    service: CourseService = Depends(get_course_service),
    _=Depends(require_admin),
):
    return service.create_course(payload)


@router.put("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: int,
    payload: CourseUpdate,
    service: CourseService = Depends(get_course_service),
    _=Depends(require_admin),
):
    return service.update_course(course_id, payload)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    service: CourseService = Depends(get_course_service),
    _=Depends(require_admin),
):
    service.delete_course(course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{course_id}/compacts", response_model=CourseCompactUploadRead, status_code=status.HTTP_201_CREATED)
async def upload_course_compact(
    course_id: int,
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    service: CourseService = Depends(get_course_service),
):
    compact, imported_topics = service.upload_course_compact(
        course_id=course_id,
        title=title,
        upload_file=file,
        admin_user_id=current_user.id,
    )
    payload = CourseCompactRead.model_validate(compact).model_dump()
    payload["imported_topics"] = imported_topics
    return payload


@router.get("/{course_id}/compacts", response_model=list[CourseCompactRead])
async def list_course_compacts(
    course_id: int,
    active_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_current_user),
    service: CourseService = Depends(get_course_service),
):
    return service.list_course_compacts(course_id, active_only=active_only, skip=skip, limit=limit)


@router.get("/{course_id}/compact-active", response_model=CourseCompactRead)
async def get_active_course_compact(
    course_id: int,
    _: User = Depends(get_current_user),
    service: CourseService = Depends(get_course_service),
):
    return service.get_active_compact(course_id)


@router.post("/{course_id}/compacts/{compact_id}/activate", response_model=CourseCompactRead)
async def activate_course_compact(
    course_id: int,
    compact_id: int,
    _: User = Depends(require_admin),
    service: CourseService = Depends(get_course_service),
):
    return service.activate_compact(course_id, compact_id)


@router.post("/{course_id}/compacts/{compact_id}/import-topics", response_model=TopicBulkUpsertResult)
async def import_topics_from_compact(
    course_id: int,
    compact_id: int,
    _: User = Depends(require_admin),
    service: CourseService = Depends(get_course_service),
):
    return service.import_topics_from_compact(course_id=course_id, compact_id=compact_id)
