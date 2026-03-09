from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.topics.models import Topic


class TopicRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, course_id: int | None = None) -> list[Topic]:
        stmt = select(Topic).order_by(Topic.name)
        if course_id:
            stmt = stmt.where(Topic.course_id == course_id)
        return list(self.db.scalars(stmt))

    def get(self, topic_id: int) -> Topic | None:
        return self.db.get(Topic, topic_id)
