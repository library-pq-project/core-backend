from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.questions.repository import QuestionRepository
from src.modules.questions.schemas import QuestionRead
from src.modules.questions.service import QuestionService

router = APIRouter()


def get_question_service(db: Session = Depends(get_db)) -> QuestionService:
    return QuestionService(QuestionRepository(db))


@router.get("", response_model=list[QuestionRead])
async def list_questions(
    course_id: int | None = Query(default=None),
    topic_id: int | None = Query(default=None),
    year: int | None = Query(default=None),
    question_type: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    service: QuestionService = Depends(get_question_service),
):
    return service.list_questions(
        course_id=course_id,
        topic_id=topic_id,
        year=year,
        question_type=question_type,
        source_type=source_type,
    )


@router.get("/{question_id}", response_model=QuestionRead)
async def get_question(question_id: int, service: QuestionService = Depends(get_question_service)):
    return service.get_question(question_id)
