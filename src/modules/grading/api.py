from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.analytics.repository import AnalyticsRepository
from src.modules.auth.api import get_current_user
from src.modules.auth.models import User
from src.modules.grading.repository import GradingRepository
from src.modules.grading.schemas import GradeQuizResponse
from src.modules.grading.service import GradingService
from src.modules.quizzes.repository import QuizRepository

router = APIRouter()


def get_grading_service(db: Session = Depends(get_db)) -> GradingService:
    return GradingService(
        grading_repository=GradingRepository(db),
        quiz_repository=QuizRepository(db),
        analytics_repository=AnalyticsRepository(db),
    )


@router.post("/{quiz_id}/attempts/{attempt_id}/grade", response_model=GradeQuizResponse)
async def grade_attempt(
    quiz_id: int,
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    service: GradingService = Depends(get_grading_service),
):
    result = service.grade_quiz(quiz_id, current_user.id, attempt_id=attempt_id)
    return GradeQuizResponse(
        attempt_id=result.attempt_id,
        quiz_id=result.quiz_id,
        graded=True,
        total_score=float(result.total_score),
        max_score=float(result.max_score),
        percentage_score=float(result.percentage_score),
    )


@router.post("/{quiz_id}/grade", response_model=GradeQuizResponse)
async def grade_quiz(
    quiz_id: int,
    attempt_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: GradingService = Depends(get_grading_service),
    db: Session = Depends(get_db),
):
    if attempt_id is None:
        latest = QuizRepository(db).get_latest_attempt(quiz_id, current_user.id)
        if latest is None:
            raise HTTPException(status_code=404, detail="No attempt found")
        attempt_id = latest.id

    result = service.grade_quiz(quiz_id, current_user.id, attempt_id=attempt_id)
    return GradeQuizResponse(
        attempt_id=result.attempt_id,
        quiz_id=result.quiz_id,
        graded=True,
        total_score=float(result.total_score),
        max_score=float(result.max_score),
        percentage_score=float(result.percentage_score),
    )
