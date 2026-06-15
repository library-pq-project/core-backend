from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.common.errors import bad_request
from src.db.session import get_db
from src.modules.auth.api import get_current_user
from src.modules.auth.models import User
from src.modules.quizzes.repository import QuizRepository
from src.modules.quizzes.schemas import (
    QuizAttemptRead,
    QuizCreate,
    QuizQuestionRead,
    QuizRead,
    QuizSubmitInput,
    StartAttemptInput,
)
from src.modules.quizzes.service import QuizService

router = APIRouter()


def get_quiz_service(db: Session = Depends(get_db)) -> QuizService:
    return QuizService(QuizRepository(db))


@router.post("", response_model=QuizRead)
async def create_quiz(
    payload: QuizCreate,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    return service.create_quiz(payload, current_user.id)


@router.get("", response_model=list[QuizRead])
async def list_quizzes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    return service.list_quizzes(current_user.id, skip=skip, limit=limit)


@router.get("/{quiz_id}", response_model=QuizRead)
async def get_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    return service.get_quiz(quiz_id, current_user.id)


@router.get("/{quiz_id}/questions", response_model=list[QuizQuestionRead])
async def get_quiz_questions(
    quiz_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    quiz = service.get_quiz(quiz_id, current_user.id)
    questions = sorted(quiz.quiz_questions, key=lambda item: item.sequence_number)
    return questions[skip : skip + limit]


@router.post("/{quiz_id}/attempts/start", response_model=QuizAttemptRead)
async def start_attempt(
    quiz_id: int,
    payload: StartAttemptInput,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    return service.start_attempt(
        quiz_id,
        current_user.id,
        selected_duration_minutes=payload.selected_duration_minutes,
    )


@router.post("/{quiz_id}/attempts/{attempt_id}/submit", response_model=QuizAttemptRead, include_in_schema=False)
async def submit_attempt_compat(
    quiz_id: int,
    attempt_id: int,
    payload: QuizSubmitInput,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    attempt = service.get_attempt_by_id(attempt_id, current_user.id)
    if attempt.quiz_id != quiz_id:
        raise bad_request(
            f"Attempt with id {attempt_id} belongs to quiz with id {attempt.quiz_id}, not quiz with id {quiz_id}",
            error_code="QUIZ_ATTEMPT_MISMATCH",
            resource="attempt",
            resource_id=attempt_id,
            extra={"quiz_id": quiz_id, "actual_quiz_id": attempt.quiz_id},
        )
    return service.submit_attempt_by_id(
        attempt_id=attempt_id,
        user_id=current_user.id,
        payload=payload,
    )
