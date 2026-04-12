from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.common.enums import QuizStatus
from src.db.session import get_db
from src.modules.auth.api import get_current_user
from src.modules.auth.models import User
from src.modules.quizzes.repository import QuizRepository
from src.modules.quizzes.schemas import AttemptResultRead, QuizAttemptQuestionRead, QuizReviewResponse
from src.modules.quizzes.service import QuizService

router = APIRouter()


def get_quiz_service(db: Session = Depends(get_db)) -> QuizService:
    return QuizService(QuizRepository(db))


@router.get("/{attempt_id}/questions", response_model=list[QuizAttemptQuestionRead])
async def get_attempt_questions(
    attempt_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    quiz, _attempt, responses = service.get_attempt_questions_by_attempt_id(attempt_id, current_user.id)
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


@router.get("/{attempt_id}/review", response_model=QuizReviewResponse)
async def get_attempt_review(
    attempt_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = QuizRepository(db)
    attempt = repository.get_attempt_by_id(attempt_id, current_user.id)
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    quiz = repository.get_user_quiz(attempt.quiz_id, current_user.id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

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

    return {"quiz_id": quiz.id, "attempt_id": attempt_id, "items": items[skip : skip + limit]}


@router.get("/{attempt_id}/result", response_model=AttemptResultRead)
async def get_attempt_result(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = QuizRepository(db)
    attempt = repository.get_attempt_by_id(attempt_id, current_user.id)
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    result = repository.get_result(attempt.quiz_id, current_user.id, attempt_id=attempt_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    topic_metrics = repository.list_attempt_topic_metrics(attempt_id, current_user.id)
    topic_analysis = []
    for metric in topic_metrics:
        attempted_count = int(metric.attempted_count)
        correct_count = int(metric.correct_count)
        accuracy = (correct_count / attempted_count * 100) if attempted_count > 0 else 0.0
        topic_analysis.append(
            {
                "topic_id": metric.topic_id,
                "attempted_count": attempted_count,
                "correct_count": correct_count,
                "accuracy_rate": round(accuracy, 2),
                "score": float(metric.score),
            }
        )
    return {
        "attempt_id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "expected_end_at": attempt.expected_end_at,
        "submitted_at": attempt.submitted_at,
        "duration_used_seconds": attempt.duration_used_seconds,
        "selected_duration_minutes": attempt.selected_duration_minutes,
        "total_score": float(result.total_score),
        "max_score": float(result.max_score),
        "percentage_score": float(result.percentage_score),
        "correct_count": result.correct_count,
        "wrong_count": result.wrong_count,
        "unanswered_count": result.unanswered_count,
        "topic_analysis": topic_analysis,
    }
