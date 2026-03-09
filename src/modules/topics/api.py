from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.topics.repository import TopicRepository
from src.modules.topics.schemas import TopicRead
from src.modules.topics.service import TopicService

router = APIRouter()


def get_topic_service(db: Session = Depends(get_db)) -> TopicService:
    return TopicService(TopicRepository(db))


@router.get("", response_model=list[TopicRead])
async def list_topics(
    course_id: int | None = Query(default=None),
    service: TopicService = Depends(get_topic_service),
):
    return service.list_topics(course_id=course_id)


@router.get("/{topic_id}", response_model=TopicRead)
async def get_topic(topic_id: int, service: TopicService = Depends(get_topic_service)):
    return service.get_topic(topic_id)
