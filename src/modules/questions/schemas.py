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
