from src.modules.analytics.repository import AnalyticsRepository
from src.modules.analytics.schemas import AnalyticsOverview, AttemptTopicMetricRead, TopicPerformanceRead


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

    def get_topic_performance(
        self,
        *,
        user_id: int,
        course_id: int | None = None,
        academic_session_id: int | None = None,
        topic_id: int | None = None,
    ) -> list[TopicPerformanceRead]:
        rows = self.repository.aggregate_topic_metrics(
            user_id=user_id,
            course_id=course_id,
            academic_session_id=academic_session_id,
            topic_id=topic_id,
        )
        output: list[TopicPerformanceRead] = []
        for row in rows:
            attempted = int(row[2] or 0)
            correct = int(row[3] or 0)
            avg_score = float(row[4] or 0)
            accuracy = (correct / attempted * 100) if attempted else 0
            weakness = "low" if accuracy >= 70 else "medium" if accuracy >= 40 else "high"
            output.append(
                TopicPerformanceRead(
                    course_id=row[0],
                    topic_id=row[1],
                    topic_name=None,
                    questions_attempted=attempted,
                    questions_correct=correct,
                    accuracy_rate=round(accuracy, 2),
                    weakness_level=weakness,
                )
            )
        return output

    def list_attempt_metrics(self, user_id: int, *, skip: int, limit: int) -> list[AttemptTopicMetricRead]:
        records = self.repository.list_attempt_metrics(user_id, skip=skip, limit=limit)
        return [
            AttemptTopicMetricRead(
                attempt_id=record.attempt_id,
                course_id=record.course_id,
                topic_id=record.topic_id,
                academic_session_id=record.academic_session_id,
                attempted_count=record.attempted_count,
                correct_count=record.correct_count,
                score=float(record.score),
            )
            for record in records
        ]
