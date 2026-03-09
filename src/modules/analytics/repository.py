from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.modules.analytics.models import TopicPerformance
from src.modules.quizzes.models import QuizResponse


class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_topic_performance(self, *, user_id: int, course_id: int, topic_id: int | None) -> TopicPerformance | None:
        stmt = select(TopicPerformance).where(
            TopicPerformance.user_id == user_id,
            TopicPerformance.course_id == course_id,
            TopicPerformance.topic_id == topic_id,
        )
        return self.db.scalar(stmt)

    def save_topic_performance(self, record: TopicPerformance) -> TopicPerformance:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_topic_performance(self, user_id: int) -> list[TopicPerformance]:
        stmt = select(TopicPerformance).where(TopicPerformance.user_id == user_id)
        return list(self.db.scalars(stmt))

    def overview(self, user_id: int) -> tuple[int, int, int, float]:
        from src.modules.quizzes.models import Quiz, QuizResult

        quizzes_taken = self.db.scalar(select(func.count(Quiz.id)).where(Quiz.user_id == user_id)) or 0
        attempted = (
            self.db.scalar(select(func.count(QuizResponse.id)).where(QuizResponse.user_id == user_id)) or 0
        )
        correct = (
            self.db.scalar(
                select(func.count(QuizResponse.id)).where(
                    QuizResponse.user_id == user_id, QuizResponse.is_correct.is_(True)
                )
            )
            or 0
        )
        average_percentage = (
            self.db.scalar(select(func.avg(QuizResult.percentage_score)).where(QuizResult.user_id == user_id))
            or 0
        )
        return int(quizzes_taken), int(attempted), int(correct), float(average_percentage)
