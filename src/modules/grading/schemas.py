from pydantic import BaseModel


class GradeQuizResponse(BaseModel):
    quiz_id: int
    graded: bool
    total_score: float
    max_score: float
    percentage_score: float
