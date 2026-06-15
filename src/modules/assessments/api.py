from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Literal

from src.db.session import get_db
from src.modules.assessments.repository import AssessmentRepository
from src.modules.assessments.schemas import (
    AssessmentCreate,
    AssessmentListItem,
    AssessmentPracticeConfigRead,
    AssessmentPracticeStartInput,
    AssessmentPracticeStartResponse,
    AssessmentRead,
)
from src.modules.assessments.service import AssessmentService
from src.modules.auth.api import get_current_user, require_admin
from src.modules.auth.models import User
from src.modules.questions.schemas import QuestionRead
from src.modules.quizzes.schemas import QuizAttemptRead
from src.modules.quizzes.service import QuizService
from src.modules.quizzes.repository import QuizRepository

router = APIRouter()


def get_assessment_service(db: Session = Depends(get_db)) -> AssessmentService:
    return AssessmentService(AssessmentRepository(db))


def get_quiz_service(db: Session = Depends(get_db)) -> QuizService:
    return QuizService(QuizRepository(db))


@router.post("", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    payload: AssessmentCreate,
    service: AssessmentService = Depends(get_assessment_service),
    _=Depends(require_admin),
):
    return service.create_assessment(payload)


@router.get("", response_model=list[AssessmentListItem])
async def list_assessments(
    course_id: int | None = Query(default=None),
    academic_session_id: int | None = Query(default=None),
    semester_id: int | None = Query(default=None),
    assessment_type: str | None = Query(default=None),
    source_type: Literal["actual", "ai_generated"] | None = Query(default=None),
    mine_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: AssessmentService = Depends(get_assessment_service),
    current_user: User = Depends(get_current_user),
):
    owner_filter = current_user.id if mine_only else None
    return service.list_assessments(
        course_id=course_id,
        academic_session_id=academic_session_id,
        semester_id=semester_id,
        assessment_type=assessment_type,
        source_type=source_type,
        created_by_user_id=owner_filter,
        skip=skip,
        limit=limit,
    )


@router.get("/{assessment_id}/practice-config", response_model=AssessmentPracticeConfigRead)
async def get_assessment_practice_config(
    assessment_id: int,
    service: AssessmentService = Depends(get_assessment_service),
    _: User = Depends(get_current_user),
):
    return service.get_practice_config(assessment_id)


@router.post("/{assessment_id}/practice/start", response_model=AssessmentPracticeStartResponse, status_code=status.HTTP_201_CREATED)
async def start_practice_from_assessment(
    assessment_id: int,
    payload: AssessmentPracticeStartInput,
    current_user: User = Depends(get_current_user),
    assessment_service: AssessmentService = Depends(get_assessment_service),
    quiz_service: QuizService = Depends(get_quiz_service),
):
    assessment_service.get_assessment(assessment_id)
    quiz, attempt, available_count = quiz_service.create_and_start_practice_from_assessment(
        assessment_id=assessment_id,
        user_id=current_user.id,
        desired_question_count=payload.desired_question_count,
        selected_topic_ids=payload.selected_topic_ids,
        selected_duration_minutes=payload.selected_duration_minutes,
        reveal_answers_post_submit=payload.reveal_answers_post_submit,
    )
    return {
        "quiz_id": quiz.id,
        "attempt": QuizAttemptRead.model_validate(attempt),
        "available_question_count": available_count,
    }


@router.get("/{assessment_id}/questions", response_model=list[QuestionRead])
async def get_questions_in_assessment(
    assessment_id: int,
    include_correct: bool = Query(default=False),
    question_type: str | None = Query(default=None),
    source_type: Literal["actual", "ai_generated"] | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: AssessmentService = Depends(get_assessment_service),
):
    questions = service.list_assessment_questions(
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
                "marking_scheme": question.marking_scheme if allow_correct else None,
                "explanation": question.explanation if allow_correct else None,
                "ai_topic_confidence": float(question.ai_topic_confidence) if question.ai_topic_confidence is not None else None,
                "ai_topic_trace": question.ai_topic_trace,
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
