from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.auth.api import get_current_user
from src.modules.auth.models import User
from src.modules.quizzes.repository import QuizRepository
from src.modules.quizzes.schemas import (
    QuizCreate,
    QuizQuestionRead,
    QuizRead,
    QuizReviewResponse,
    QuizResultRead,
    QuizSubmitInput,
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


@router.post("/{quiz_id}/start", response_model=QuizRead)
async def start_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    return service.start_quiz(quiz_id, current_user.id)


@router.post("/{quiz_id}/submit", response_model=QuizRead)
async def submit_quiz(
    quiz_id: int,
    payload: QuizSubmitInput,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    return service.submit_quiz(quiz_id, current_user.id, payload)


@router.get("/{quiz_id}/result", response_model=QuizResultRead)
async def get_quiz_result(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = QuizRepository(db)
    result = repository.get_result(quiz_id, current_user.id)
    if not result:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz result not found")
    return result


@router.get("/{quiz_id}/review", response_model=QuizReviewResponse)
async def get_quiz_review(
    quiz_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = QuizRepository(db).get_user_quiz(quiz_id, current_user.id)
    if not quiz:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    responses = {response.quiz_question_id: response for response in QuizRepository(db).list_responses_for_quiz(quiz_id, current_user.id)}

    items = []
    for quiz_question in sorted(quiz.quiz_questions, key=lambda item: item.sequence_number):
        response = responses.get(quiz_question.id)
        selected_option = None
        correct_option = None
        if response and response.selected_quiz_question_option_id:
            selected_option = next(
                (option for option in quiz_question.options if option.id == response.selected_quiz_question_option_id),
                None,
            )
        if quiz_question.question_type == "objective":
            correct_option = next((option for option in quiz_question.options if option.is_correct_snapshot), None)

        items.append(
            {
                "quiz_question_id": quiz_question.id,
                "question_text": quiz_question.question_snapshot_text,
                "question_type": quiz_question.question_type,
                "selected_option_id": selected_option.id if selected_option else None,
                "selected_option_text": selected_option.option_text_snapshot if selected_option else None,
                "correct_option_id": correct_option.id if correct_option else None,
                "correct_option_text": correct_option.option_text_snapshot if correct_option else None,
                "answer_text": response.answer_text if response else None,
                "feedback": response.feedback if response else None,
                "explanation": quiz_question.question.explanation if quiz_question.question else None,
                "is_correct": response.is_correct if response else None,
                "score_awarded": float(response.score_awarded) if response and response.score_awarded is not None else None,
            }
        )

    return {"quiz_id": quiz_id, "items": items[skip : skip + limit]}
