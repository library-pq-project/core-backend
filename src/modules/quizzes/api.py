from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.common.enums import QuizStatus
from src.db.session import get_db
from src.modules.auth.api import get_current_user
from src.modules.auth.models import User
from src.modules.quizzes.repository import QuizRepository
from src.modules.quizzes.schemas import (
    QuizAttemptQuestionRead,
    QuizAttemptRead,
    QuizCreate,
    QuizQuestionRead,
    QuizRead,
    QuizReviewResponse,
    QuizResultRead,
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


@router.get("/{quiz_id}/in-progress-questions", response_model=list[QuizAttemptQuestionRead])
async def get_in_progress_questions(
    quiz_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: QuizService = Depends(get_quiz_service),
):
    quiz, attempt = service.get_in_progress_questions(quiz_id, current_user.id)
    responses = {
        response.quiz_question_id: response
        for response in QuizRepository(db).list_responses_for_attempt(attempt.id, current_user.id)
    }
    questions = sorted(quiz.quiz_questions, key=lambda item: item.sequence_number)[skip : skip + limit]
    return [
        {
            "quiz_question_id": question.id,
            "question_text": question.question_snapshot_text,
            "question_type": question.question_type,
            "sequence_number": question.sequence_number,
            "options": sorted(question.options, key=lambda item: item.display_order),
            "selected_quiz_question_option_id": responses.get(question.id).selected_quiz_question_option_id
            if responses.get(question.id)
            else None,
            "answer_text": responses.get(question.id).answer_text if responses.get(question.id) else None,
        }
        for question in questions
    ]


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


@router.post("/{quiz_id}/start", response_model=QuizRead)
async def start_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    return service.start_quiz(quiz_id, current_user.id)


@router.post("/{quiz_id}/attempts/{attempt_id}/submit", response_model=QuizAttemptRead)
async def submit_attempt(
    quiz_id: int,
    attempt_id: int,
    payload: QuizSubmitInput,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    return service.submit_quiz_for_attempt(
        quiz_id=quiz_id,
        user_id=current_user.id,
        attempt_id=attempt_id,
        payload=payload,
    )


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
    attempt_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = QuizRepository(db)
    result = repository.get_result(quiz_id, current_user.id, attempt_id=attempt_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz result not found")
    return result


@router.get("/{quiz_id}/attempts/{attempt_id}/review", response_model=QuizReviewResponse)
async def get_attempt_review(
    quiz_id: int,
    attempt_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = QuizRepository(db)
    quiz = repository.get_user_quiz(quiz_id, current_user.id)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    attempt = repository.get_attempt(quiz_id, attempt_id, current_user.id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    responses = {
        response.quiz_question_id: response
        for response in repository.list_responses_for_attempt(attempt_id, current_user.id)
    }

    allow_correct_visibility = bool(
        quiz.reveal_answers_post_submit and attempt.status in [QuizStatus.SUBMITTED.value, QuizStatus.GRADED.value]
    )

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
        if allow_correct_visibility and quiz_question.question_type == "objective":
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
                "explanation": quiz_question.question.explanation if quiz_question.question and allow_correct_visibility else None,
                "is_correct": response.is_correct if response else None,
                "score_awarded": float(response.score_awarded) if response and response.score_awarded is not None else None,
            }
        )

    return {"quiz_id": quiz_id, "attempt_id": attempt_id, "items": items[skip : skip + limit]}


@router.get("/{quiz_id}/review", response_model=QuizReviewResponse)
async def get_quiz_review(
    quiz_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    latest = QuizRepository(db).get_latest_attempt(quiz_id, current_user.id)
    if latest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No attempt found")
    return await get_attempt_review(
        quiz_id=quiz_id,
        attempt_id=latest.id,
        skip=skip,
        limit=limit,
        current_user=current_user,
        db=db,
    )
