from pydantic import BaseModel, Field

from src.modules.questions.schemas import QuestionRead


class AIQuestionGenerationCreate(BaseModel):
    course_id: int
    topic_id: int | None = None
    lecture_note_id: int | None = None
    question_type: str
    requested_count: int = Field(ge=1, le=100)


class AIQuestionGenerationResponse(BaseModel):
    fingerprint: str
    reused_count: int
    generated_count: int
    questions: list[QuestionRead]
