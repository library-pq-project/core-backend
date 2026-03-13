from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.auth.api import get_current_user, require_admin
from src.modules.auth.models import User
from src.modules.questions.repository import QuestionRepository
from src.modules.questions.schemas import QuestionCreate, QuestionRead, QuestionUpdate
from src.modules.questions.service import QuestionService

router = APIRouter()


def get_question_service(db: Session = Depends(get_db)) -> QuestionService:
    return QuestionService(QuestionRepository(db))


@router.get("", response_model=list[QuestionRead])
async def list_questions(
    assessment_id: int | None = Query(default=None),
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
        assessment_id=assessment_id,
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


@router.get("/{question_id}/options", response_model=list[dict])
async def get_question_options(
    question_id: int,
    include_correct: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    service: QuestionService = Depends(get_question_service),
):
    question = service.get_question(question_id)
    allow_correct = include_correct and current_user.role == "admin"
    output = []
    for option in sorted(question.options, key=lambda item: item.position):
        item = {
            "id": option.id,
            "option_text": option.option_text,
            "position": option.position,
        }
        if allow_correct:
            item["is_correct"] = option.is_correct
        output.append(item)
    return output


@router.post("", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
async def create_question(
    payload: QuestionCreate,
    service: QuestionService = Depends(get_question_service),
    _=Depends(require_admin),
):
    return service.create_question(payload)


@router.put("/{question_id}", response_model=QuestionRead)
async def update_question(
    question_id: int,
    payload: QuestionUpdate,
    service: QuestionService = Depends(get_question_service),
    _=Depends(require_admin),
):
    return service.update_question(question_id, payload)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    service: QuestionService = Depends(get_question_service),
    _=Depends(require_admin),
):
    service.delete_question(question_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
