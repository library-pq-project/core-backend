from fastapi import HTTPException, status

from src.modules.topics.models import Topic
from src.modules.topics.repository import TopicRepository


class TopicService:
    def __init__(self, repository: TopicRepository):
        self.repository = repository

    def list_topics(self, course_id: int | None = None) -> list[Topic]:
        return self.repository.list(course_id=course_id)

    def get_topic(self, topic_id: int) -> Topic:
        topic = self.repository.get(topic_id)
        if not topic:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
        return topic
