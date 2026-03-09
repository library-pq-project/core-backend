from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.common.utils import generate_slug
from src.modules.topics.models import Topic
from src.modules.topics.repository import TopicRepository
from src.modules.topics.schemas import TopicCreate, TopicUpdate


class TopicService:
    def __init__(self, repository: TopicRepository):
        self.repository = repository

    def list_topics(self, *, course_id: int | None = None, skip: int, limit: int) -> list[Topic]:
        return self.repository.list(course_id=course_id, skip=skip, limit=limit)

    def get_topic(self, topic_id: int) -> Topic:
        topic = self.repository.get(topic_id)
        if not topic:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
        return topic

    def create_topic(self, payload: TopicCreate) -> Topic:
        topic = Topic(
            course_id=payload.course_id,
            name=payload.name,
            slug=payload.slug or generate_slug(payload.name),
            description=payload.description,
        )
        try:
            return self.repository.create(topic)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unable to create topic with provided values",
            ) from exc

    def update_topic(self, topic_id: int, payload: TopicUpdate) -> Topic:
        topic = self.get_topic(topic_id)
        updates = payload.model_dump(exclude_unset=True)

        if "course_id" in updates:
            topic.course_id = updates["course_id"]
        if "name" in updates:
            topic.name = updates["name"]
        if "slug" in updates:
            topic.slug = updates["slug"]
        elif "name" in updates:
            topic.slug = generate_slug(updates["name"])
        if "description" in updates:
            topic.description = updates["description"]

        try:
            return self.repository.save(topic)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unable to update topic with provided values",
            ) from exc

    def delete_topic(self, topic_id: int) -> None:
        topic = self.get_topic(topic_id)
        self.repository.delete(topic)
