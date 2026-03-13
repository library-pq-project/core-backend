from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.academic.repository import AcademicRepository
from src.modules.academic.service import AcademicService
from src.modules.auth.api import get_current_user
from src.modules.auth.models import User
from src.modules.questions.schemas import QuestionRead

router = APIRouter()


def get_academic_service(db: Session = Depends(get_db)) -> AcademicService:
    return AcademicService(AcademicRepository(db))


@router.get("/{assessment_id}/questions", response_model=list[QuestionRead])
async def get_questions_in_assessment(
    assessment_id: int,
    include_correct: bool = Query(default=False),
    question_type: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: AcademicService = Depends(get_academic_service),
):
    questions = service.list_questions_in_assessment(
        assessment_id=assessment_id,
        question_type=question_type,
        source_type=source_type,
        skip=skip,
        limit=limit,
    )

    allow_correct = bool(include_correct and current_user.role == "admin")
    output = []
    for question in questions:
        output.append(
            {
                "id": question.id,
                "assessment_id": question.assessment_id,
                "course_id": question.course_id,
                "topic_id": question.topic_id,
                "lecture_note_id": question.lecture_note_id,
                "year": question.year,
                "question_text": question.question_text,
                "source_text": question.source_text,
                "content_format": question.content_format,
                "question_type": question.question_type,
                "source_type": question.source_type,
                "difficulty_level": question.difficulty_level,
                "mark_allocation": float(question.mark_allocation),
                "explanation": question.explanation if allow_correct else None,
                "created_at": question.created_at,
                "options": [
                    {
                        "id": option.id,
                        "option_text": option.option_text,
                        "position": option.position,
                        "is_correct": option.is_correct if allow_correct else None,
                    }
                    for option in sorted(question.options, key=lambda item: item.position)
                ],
            }
        )
    return output
