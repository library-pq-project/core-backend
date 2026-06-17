from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class QuestionOptionRead(BaseModel):
    id: int
    option_text: str
    position: int
    is_correct: bool | None = None

    model_config = {"from_attributes": True}


class QuestionRead(BaseModel):
    id: int
    assessment_id: int | None
    course_id: int
    topic_id: int | None
    lecture_note_id: int | None
    year: int | None
    question_text: str
    source_text: str | None
    content_format: Literal["plain_text", "markdown_latex"]
    question_type: str
    source_type: str
    difficulty_level: str | None
    mark_allocation: float
    marking_scheme: str | None
    explanation: str | None
    ai_topic_confidence: float | None = None
    ai_topic_trace: dict | None = None
    created_at: datetime
    options: list[QuestionOptionRead] = []

    model_config = {"from_attributes": True}


class QuestionOptionWrite(BaseModel):
    option_text: str
    is_correct: bool = False
    position: int


class QuestionCreate(BaseModel):
    assessment_id: int
    course_id: int | None = None
    topic_id: int | None = None
    lecture_note_id: int | None = None
    year: int | None = None
    question_text: str | None = None
    source_text: str | None = None
    content_format: Literal["plain_text", "markdown_latex"] = "plain_text"
    question_type: Literal["objective", "theory", "practical", "case_based"]
    source_type: Literal["actual", "ai_generated"]
    difficulty_level: str | None = None
    mark_allocation: float = 1.0
    marking_scheme: str | None = None
    solution_text: str | None = None
    explanation: str | None = None
    is_active: bool = True
    options: list[QuestionOptionWrite] = []


class QuestionUpdate(BaseModel):
    assessment_id: int | None = None
    course_id: int | None = None
    topic_id: int | None = None
    lecture_note_id: int | None = None
    year: int | None = None
    question_text: str | None = None
    source_text: str | None = None
    content_format: Literal["plain_text", "markdown_latex"] | None = None
    question_type: Literal["objective", "theory", "practical", "case_based"] | None = None
    source_type: Literal["actual", "ai_generated"] | None = None
    difficulty_level: str | None = None
    mark_allocation: float | None = None
    marking_scheme: str | None = None
    solution_text: str | None = None
    explanation: str | None = None
    is_active: bool | None = None
    options: list[QuestionOptionWrite] | None = None


class BulkQuestionRow(BaseModel):
    assessment_id: int | None = None
    course_id: int | None = None
    topic_id: int | None = None
    topic_name: str | None = None
    lecture_note_id: int | None = None
    year: int | None = None
    question_text: str | None = None
    source_text: str | None = None
    content_format: Literal["plain_text", "markdown_latex"] = "plain_text"
    question_type: Literal["objective", "theory", "practical", "case_based"] | None = None
    source_type: Literal["actual", "ai_generated"] | None = None
    difficulty_level: Literal["easy", "medium", "hard", "mixed"] | None = None
    mark_allocation: float = 1.0
    marking_scheme: str | None = None
    solution_text: str | None = None
    explanation: str | None = None
    is_active: bool = True
    options: list[QuestionOptionWrite] = []


class BulkQuestionImportRequest(BaseModel):
    rows: list[BulkQuestionRow]
    import_mode: Literal["objective", "theory", "mixed"] = "mixed"
    default_course_id: int | None = None
    default_assessment_id: int | None = None
    default_academic_session_id: int | None = None
    default_semester_id: int | None = None
    default_assessment_type: str | None = None
    default_question_format: str | None = None
    default_duration_minutes: int = 60
    default_source_type: Literal["actual", "ai_generated"] = "actual"
    auto_categorize_topics: bool = True
    draft_theory_without_solution: bool = False


class ImportRowError(BaseModel):
    row_number: int
    errors: list[str]


class QuestionImportJobRead(BaseModel):
    id: int
    created_by_user_id: int
    status: str
    source_type: str
    file_name: str | None
    import_mode: str
    total_rows: int
    accepted_count: int
    rejected_count: int
    row_errors: list[dict[str, Any]] | None
    created_question_ids: list[int] | None
    created_topic_ids: list[int] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BulkImportResult(BaseModel):
    job: QuestionImportJobRead
    accepted_count: int
    rejected_count: int
    errors: list[ImportRowError]
    created_question_ids: list[int]
    created_topic_ids: list[int]
    created_assessment_id: int | None = None
