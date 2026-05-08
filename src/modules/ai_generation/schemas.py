from typing import Literal

from pydantic import BaseModel, Field

from src.modules.questions.schemas import QuestionRead


class AIQuestionGenerationCreate(BaseModel):
    quiz_title: str
    user_prompt: str
    course_id: int
    topic_ids: list[int] | None = None
    lecture_note_id: int | None = None
    question_type: str
    exam_type: Literal["objective", "theory", "mixed"]
    difficulty_level: Literal["easy", "medium", "hard", "mixed"] = "mixed"
    requested_count: int = Field(ge=1, le=100)


class AIQuestionGenerationResponse(BaseModel):
    fingerprint: str
    reused_count: int
    generated_count: int
    model_name: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    questions: list[QuestionRead]
