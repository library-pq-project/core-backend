from fastapi import HTTPException, status

from src.modules.questions.models import Question
from src.modules.questions.repository import QuestionRepository


class QuestionService:
    def __init__(self, repository: QuestionRepository):
        self.repository = repository

    def list_questions(
        self,
        *,
        course_id: int | None,
        topic_id: int | None,
        year: int | None,
        question_type: str | None,
        source_type: str | None,
    ) -> list[Question]:
        return self.repository.list(
            course_id=course_id,
            topic_id=topic_id,
            year=year,
            question_type=question_type,
            source_type=source_type,
        )

    def get_question(self, question_id: int) -> Question:
        question = self.repository.get(question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        return question
