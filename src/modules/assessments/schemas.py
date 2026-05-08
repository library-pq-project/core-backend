from pydantic import BaseModel, Field
from src.modules.quizzes.schemas import QuizAttemptRead, QuizRead


class AssessmentCreate(BaseModel):
    course_id: int
    academic_session_id: int
    semester_id: int | None = None
    assessment_type: str
    question_format: str
    default_duration_minutes: int = Field(default=60, ge=1, le=600)
    year_label: str | None = None


class AssessmentRead(BaseModel):
    id: int
    course_id: int
    academic_session_id: int
    semester_id: int | None
    assessment_type: str
    question_format: str
    default_duration_minutes: int
    year_label: str | None
    source_type: str
    created_by_user_id: int | None
    slug: str

    model_config = {"from_attributes": True}


class AssessmentListItem(BaseModel):
    id: int
    slug: str
    title_label: str
    course_id: int
    academic_session_id: int
    semester_id: int | None
    year_label: str | None
    assessment_type: str
    question_format: str
    source_type: str
    created_by_user_id: int | None
    default_duration_minutes: int
    total_available_questions: int


class AssessmentTopicOption(BaseModel):
    id: int
    name: str
    slug: str


class PracticeConstraints(BaseModel):
    min_questions: int
    max_questions: int
    min_duration_minutes: int
    max_duration_minutes: int


class AssessmentPracticeConfigRead(BaseModel):
    assessment: AssessmentListItem
    selectable_topics: list[AssessmentTopicOption]
    constraints: PracticeConstraints


class AssessmentPracticeStartInput(BaseModel):
    desired_question_count: int = Field(ge=1, le=200)
    selected_topic_ids: list[int] | None = None
    selected_duration_minutes: int | None = Field(default=None, ge=1, le=600)
    reveal_answers_post_submit: bool = False


class AssessmentPracticeStartResponse(BaseModel):
    quiz: QuizRead
    attempt: QuizAttemptRead
    available_question_count: int
