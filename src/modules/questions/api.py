from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.questions.repository import QuestionRepository
from src.modules.questions.schemas import QuestionCreate, QuestionRead, QuestionUpdate
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
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: QuestionService = Depends(get_question_service),
):
    return service.list_questions(
        course_id=course_id,
        topic_id=topic_id,
        year=year,
        question_type=question_type,
        source_type=source_type,
        skip=skip,
        limit=limit,
    )


@router.get("/{question_id}", response_model=QuestionRead)
async def get_question(question_id: int, service: QuestionService = Depends(get_question_service)):
    return service.get_question(question_id)


@router.post("", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
async def create_question(payload: QuestionCreate, service: QuestionService = Depends(get_question_service)):
    return service.create_question(payload)


@router.put("/{question_id}", response_model=QuestionRead)
async def update_question(
    question_id: int,
    payload: QuestionUpdate,
    service: QuestionService = Depends(get_question_service),
):
    return service.update_question(question_id, payload)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(question_id: int, service: QuestionService = Depends(get_question_service)):
    service.delete_question(question_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
