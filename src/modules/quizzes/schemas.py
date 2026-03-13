from datetime import datetime

from pydantic import BaseModel, Field


class QuizCreate(BaseModel):
    title: str
    course_id: int
    topic_id: int | None = None
    academic_session_id: int | None = None
    semester_id: int | None = None
    question_source_mode: str
    question_type_mode: str | None = None
    total_questions: int = Field(ge=1, le=100)
    max_attempts: int = Field(default=3, ge=1, le=20)
    reveal_answers_post_submit: bool = False


class QuizRead(BaseModel):
    id: int
    title: str
    slug: str
    course_id: int
    topic_id: int | None
    academic_session_id: int | None
    semester_id: int | None
    question_source_mode: str
    question_type_mode: str | None
    total_questions: int
    max_attempts: int
    reveal_answers_post_submit: bool
    status: str
    started_at: datetime | None
    submitted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuizQuestionOptionRead(BaseModel):
    id: int
    option_text_snapshot: str
    display_order: int

    model_config = {"from_attributes": True}


class QuizQuestionRead(BaseModel):
    id: int
    question_snapshot_text: str
    question_type: str
    marks: float
    sequence_number: int
    options: list[QuizQuestionOptionRead]

    model_config = {"from_attributes": True}


class QuizAnswerInput(BaseModel):
    quiz_question_id: int
    selected_quiz_question_option_id: int | None = None
    answer_text: str | None = None


class QuizSubmitInput(BaseModel):
    responses: list[QuizAnswerInput]


class QuizAttemptRead(BaseModel):
    id: int
    quiz_id: int
    user_id: int
    attempt_number: int
    status: str
    started_at: datetime
    submitted_at: datetime | None
    graded_at: datetime | None

    model_config = {"from_attributes": True}


class QuizResultRead(BaseModel):
    attempt_id: int
    quiz_id: int
    total_score: float
    max_score: float
    percentage_score: float
    correct_count: int
    wrong_count: int
    unanswered_count: int

    model_config = {"from_attributes": True}


class QuizReviewItem(BaseModel):
    quiz_question_id: int
    question_text: str
    question_type: str
    selected_option_id: int | None
    selected_option_text: str | None
    correct_option_id: int | None
    correct_option_text: str | None
    answer_text: str | None
    feedback: str | None
    explanation: str | None
    is_correct: bool | None
    score_awarded: float | None


class QuizReviewResponse(BaseModel):
    quiz_id: int
    attempt_id: int
    items: list[QuizReviewItem]
