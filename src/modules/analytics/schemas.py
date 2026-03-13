from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    quizzes_taken: int
    total_questions_attempted: int
    total_correct_answers: int
    average_accuracy: float


class TopicPerformanceRead(BaseModel):
    course_id: int
    topic_id: int | None
    topic_name: str | None
    questions_attempted: int
    questions_correct: int
    accuracy_rate: float
    weakness_level: str


class AttemptTopicMetricRead(BaseModel):
    attempt_id: int
    course_id: int
    topic_id: int | None
    academic_session_id: int | None
    attempted_count: int
    correct_count: int
    score: float
