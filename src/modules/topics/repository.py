from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.courses.models import Course
from src.modules.topics.models import Topic


class TopicRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, *, course_id: int | None = None, skip: int, limit: int) -> list[Topic]:
        stmt = select(Topic).order_by(Topic.name)
        if course_id is not None:
            stmt = stmt.where(Topic.course_id == course_id)
        stmt = stmt.offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def get(self, topic_id: int) -> Topic | None:
        return self.db.get(Topic, topic_id)

    def get_by_slug(self, slug: str) -> Topic | None:
        return self.db.scalar(select(Topic).where(Topic.slug == slug))

    def list_by_course_slug(self, course_slug: str, *, skip: int, limit: int) -> list[Topic]:
        stmt = (
            select(Topic)
            .join(Course, Course.id == Topic.course_id)
            .where(Course.slug == course_slug)
            .order_by(Topic.name)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def create(self, topic: Topic) -> Topic:
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)
        return topic

    def save(self, topic: Topic) -> Topic:
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)
        return topic

    def delete(self, topic: Topic) -> None:
        self.db.delete(topic)
        self.db.commit()
