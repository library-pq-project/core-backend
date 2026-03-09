from datetime import datetime

from pydantic import BaseModel


class QuestionOptionRead(BaseModel):
    id: int
    option_text: str
    position: int

    model_config = {"from_attributes": True}


class QuestionRead(BaseModel):
    id: int
    course_id: int
    topic_id: int | None
    lecture_note_id: int | None
    year: int | None
    question_text: str
    question_type: str
    source_type: str
    difficulty_level: str | None
    mark_allocation: float
    explanation: str | None
    created_at: datetime
    options: list[QuestionOptionRead] = []

    model_config = {"from_attributes": True}


class QuestionOptionWrite(BaseModel):
    option_text: str
    is_correct: bool = False
    position: int


class QuestionCreate(BaseModel):
    course_id: int
    topic_id: int | None = None
    lecture_note_id: int | None = None
    year: int | None = None
    question_text: str
    question_type: str
    source_type: str
    difficulty_level: str | None = None
    mark_allocation: float = 1.0
    solution_text: str | None = None
    explanation: str | None = None
    is_active: bool = True
    options: list[QuestionOptionWrite] = []


class QuestionUpdate(BaseModel):
    course_id: int | None = None
    topic_id: int | None = None
    lecture_note_id: int | None = None
    year: int | None = None
    question_text: str | None = None
    question_type: str | None = None
    source_type: str | None = None
    difficulty_level: str | None = None
    mark_allocation: float | None = None
    solution_text: str | None = None
    explanation: str | None = None
    is_active: bool | None = None
    options: list[QuestionOptionWrite] | None = None
