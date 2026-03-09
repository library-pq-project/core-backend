from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.topics.repository import TopicRepository
from src.modules.topics.schemas import TopicCreate, TopicRead, TopicUpdate
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


@router.get("/{topic_id}", response_model=TopicRead)
async def get_topic(topic_id: int, service: TopicService = Depends(get_topic_service)):
    return service.get_topic(topic_id)


@router.post("", response_model=TopicRead, status_code=status.HTTP_201_CREATED)
async def create_topic(payload: TopicCreate, service: TopicService = Depends(get_topic_service)):
    return service.create_topic(payload)


@router.put("/{topic_id}", response_model=TopicRead)
async def update_topic(topic_id: int, payload: TopicUpdate, service: TopicService = Depends(get_topic_service)):
    return service.update_topic(topic_id, payload)


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(topic_id: int, service: TopicService = Depends(get_topic_service)):
    service.delete_topic(topic_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
