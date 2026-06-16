import re

from src.common.utils import generate_slug
from src.core.config import settings
from src.modules.topics.models import Topic
from src.modules.topics.repository import TopicRepository


class TopicCategorizationService:
    def __init__(self, topic_repository: TopicRepository):
        self.topic_repository = topic_repository

    def _tokenize(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) >= 3}

    def _ensure_uncategorized_topic(self, course_id: int) -> Topic:
        topic_name = settings.UNCATEGORIZED_TOPIC_NAME.strip() or "Uncategorized"
        slug = generate_slug(topic_name)
        existing = self.topic_repository.get_by_course_and_slug(course_id=course_id, slug=slug)
        if existing is not None:
            return existing

        topic = Topic(
            course_id=course_id,
            name=topic_name,
            slug=slug,
            description="Fallback topic for low-confidence automatic categorization.",
        )
        return self.topic_repository.create(topic)

    def _create_topic_from_question(self, course_id: int, question_text: str) -> Topic:
        title = " ".join(question_text.split()[:6]).strip() or "AI Generated Topic"
        base_slug = generate_slug(title) or "ai-generated-topic"
        candidate_slug = base_slug
        suffix = 1
        while True:
            existing = self.topic_repository.get_by_course_and_slug(course_id=course_id, slug=candidate_slug)
            if existing is None:
                break
            if existing.name.lower().strip() == title.lower().strip():
                return existing
            suffix += 1
            candidate_slug = f"{base_slug}-{suffix}"

        created = Topic(
            course_id=course_id,
            name=title.title(),
            slug=candidate_slug,
            description="Auto-created from question categorization.",
        )
        return self.topic_repository.create(created)

    def classify_question_topic(
        self,
        *,
        course_id: int,
        question_text: str,
        allowed_topic_ids: set[int] | None = None,
    ) -> tuple[int | None, float | None, dict | None]:
        topics = self.topic_repository.list(course_id=course_id, skip=0, limit=500)
        if allowed_topic_ids:
            topics = [topic for topic in topics if topic.id in allowed_topic_ids]

        if not topics:
            uncategorized = self._ensure_uncategorized_topic(course_id)
            return uncategorized.id, 0.0, {"strategy": "assigned_uncategorized_no_topics", "topic_slug": uncategorized.slug}

        question_tokens = self._tokenize(question_text)
        best_topic = None
        best_score = 0.0

        for topic in topics:
            topic_tokens = self._tokenize(topic.name)
            if topic.description:
                topic_tokens.update(self._tokenize(topic.description))
            if not topic_tokens:
                continue
            overlap = len(question_tokens.intersection(topic_tokens))
            score = overlap / max(len(topic_tokens), 1)
            if score > best_score:
                best_score = score
                best_topic = topic

        threshold = settings.TOPIC_CLASSIFICATION_CONFIDENCE_THRESHOLD
        if best_topic is not None and best_score >= threshold:
            return (
                best_topic.id,
                round(best_score, 4),
                {
                    "strategy": "matched_existing_topic",
                    "topic_slug": best_topic.slug,
                    "confidence_threshold": threshold,
                },
            )

        if settings.AUTO_CREATE_TOPIC_IF_LOW_CONFIDENCE:
            created = self._create_topic_from_question(course_id, question_text)
            return (
                created.id,
                round(best_score, 4),
                {
                    "strategy": "created_new_topic_low_confidence",
                    "topic_slug": created.slug,
                    "confidence_threshold": threshold,
                },
            )

        uncategorized = self._ensure_uncategorized_topic(course_id)
        return (
            uncategorized.id,
            round(best_score, 4),
            {
                "strategy": "assigned_uncategorized_low_confidence",
                "topic_slug": uncategorized.slug,
                "confidence_threshold": threshold,
            },
        )
