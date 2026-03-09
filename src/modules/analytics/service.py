from src.modules.analytics.models import TopicPerformance
from src.modules.analytics.repository import AnalyticsRepository
from src.modules.analytics.schemas import AnalyticsOverview, TopicPerformanceRead


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository):
        self.repository = repository

    def get_overview(self, user_id: int) -> AnalyticsOverview:
        quizzes_taken, attempted, correct, average_accuracy = self.repository.overview(user_id)
        return AnalyticsOverview(
            quizzes_taken=quizzes_taken,
            total_questions_attempted=attempted,
            total_correct_answers=correct,
            average_accuracy=average_accuracy,
        )

    def get_topic_performance(self, user_id: int) -> list[TopicPerformanceRead]:
        records = self.repository.list_topic_performance(user_id)
        output: list[TopicPerformanceRead] = []
        for record in records:
            accuracy = 0.0
            if record.questions_attempted > 0:
                accuracy = (record.questions_correct / record.questions_attempted) * 100
            output.append(
                TopicPerformanceRead(
                    course_id=record.course_id,
                    topic_id=record.topic_id,
                    topic_name=record.topic.name if record.topic else None,
                    questions_attempted=record.questions_attempted,
                    questions_correct=record.questions_correct,
                    accuracy_rate=round(accuracy, 2),
                    weakness_level=record.weakness_level,
                )
            )
        return output
