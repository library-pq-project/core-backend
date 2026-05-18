from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.auth.api import require_admin
from src.modules.topics.repository import TopicRepository
from src.modules.topics.schemas import TopicBulkUpsertRequest, TopicBulkUpsertResult, TopicCreate, TopicRead, TopicUpdate
from src.modules.topics.service import TopicService

router = APIRouter()


def get_topic_service(db: Session = Depends(get_db)) -> TopicService:
    return TopicService(TopicRepository(db))


@router.get("", response_model=list[TopicRead])
async def list_topics(
    course_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: TopicService = Depends(get_topic_service),
):
    return service.list_topics(course_id=course_id, skip=skip, limit=limit)


@router.get("/slug/{topic_slug}", response_model=TopicRead)
async def get_topic_by_slug(topic_slug: str, service: TopicService = Depends(get_topic_service)):
    return service.get_topic_by_slug(topic_slug)


@router.get("/in-course/{course_slug}", response_model=list[TopicRead])
async def get_topics_in_course(
    course_slug: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: TopicService = Depends(get_topic_service),
):
    return service.list_topics_in_course_slug(course_slug, skip=skip, limit=limit)


@router.get("/{topic_id}", response_model=TopicRead)
async def get_topic(topic_id: int, service: TopicService = Depends(get_topic_service)):
    return service.get_topic(topic_id)


@router.post("", response_model=TopicRead, status_code=status.HTTP_201_CREATED)
async def create_topic(
    payload: TopicCreate,
    service: TopicService = Depends(get_topic_service),
    _=Depends(require_admin),
):
    return service.create_topic(payload)


@router.post("/bulk-upsert", response_model=TopicBulkUpsertResult, status_code=status.HTTP_201_CREATED)
async def bulk_upsert_topics(
    payload: TopicBulkUpsertRequest,
    service: TopicService = Depends(get_topic_service),
    _=Depends(require_admin),
):
    return service.bulk_upsert_topics(payload)


@router.post("/bulk-upload", response_model=TopicBulkUpsertResult, status_code=status.HTTP_201_CREATED)
async def bulk_upload_topics(
    file: UploadFile = File(...),
    service: TopicService = Depends(get_topic_service),
    _=Depends(require_admin),
):
    content = await file.read()
    return service.bulk_upsert_topics_from_file(
        file_name=file.filename or "topics.csv",
        content=content,
    )


@router.put("/{topic_id}", response_model=TopicRead)
async def update_topic(
    topic_id: int,
    payload: TopicUpdate,
    service: TopicService = Depends(get_topic_service),
    _=Depends(require_admin),
):
    return service.update_topic(topic_id, payload)


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: int,
    service: TopicService = Depends(get_topic_service),
    _=Depends(require_admin),
):
    service.delete_topic(topic_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
