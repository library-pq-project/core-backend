from fastapi import HTTPException, status

from src.modules.questions.models import Question, QuestionOption
from src.modules.questions.repository import QuestionRepository
from src.modules.questions.schemas import QuestionCreate, QuestionUpdate


class QuestionService:
    def __init__(self, repository: QuestionRepository):
        self.repository = repository

    def list_questions(
        self,
        *,
        assessment_id: int | None,
        course_id: int | None,
        topic_id: int | None,
        year: int | None,
        question_type: str | None,
        source_type: str | None,
        skip: int,
        limit: int,
    ) -> list[Question]:
        return self.repository.list(
            course_id=course_id,
            assessment_id=assessment_id,
            topic_id=topic_id,
            year=year,
            question_type=question_type,
            source_type=source_type,
            skip=skip,
            limit=limit,
        )

    def get_question(self, question_id: int) -> Question:
        question = self.repository.get(question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        return question

    def create_question(self, payload: QuestionCreate) -> Question:
        if payload.assessment_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="assessment_id is required",
            )
        source_text = payload.source_text or payload.question_text
        if source_text is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either source_text or question_text is required",
            )
        question = Question(
            assessment_id=payload.assessment_id,
            course_id=payload.course_id,
            topic_id=payload.topic_id,
            lecture_note_id=payload.lecture_note_id,
            year=payload.year,
            question_text=payload.question_text or source_text,
            source_text=source_text,
            content_format=payload.content_format,
            question_type=payload.question_type,
            source_type=payload.source_type,
            difficulty_level=payload.difficulty_level,
            mark_allocation=payload.mark_allocation,
            solution_text=payload.solution_text,
            explanation=payload.explanation,
            is_active=payload.is_active,
        )
        question.options = [
            QuestionOption(
                option_text=item.option_text,
                is_correct=item.is_correct,
                position=item.position,
            )
            for item in payload.options
        ]
        return self.repository.create(question)

    def update_question(self, question_id: int, payload: QuestionUpdate) -> Question:
        question = self.get_question(question_id)
        updates = payload.model_dump(exclude_unset=True)

        for field in [
            "assessment_id",
            "course_id",
            "topic_id",
            "lecture_note_id",
            "year",
            "question_text",
            "source_text",
            "content_format",
            "question_type",
            "source_type",
            "difficulty_level",
            "mark_allocation",
            "solution_text",
            "explanation",
            "is_active",
        ]:
            if field in updates:
                setattr(question, field, updates[field])

        if "options" in updates and payload.options is not None:
            question.options = [
                QuestionOption(
                    option_text=item.option_text,
                    is_correct=item.is_correct,
                    position=item.position,
                )
                for item in payload.options
            ]

        return self.repository.save(question)

    def delete_question(self, question_id: int) -> None:
        question = self.get_question(question_id)
        self.repository.delete(question)
