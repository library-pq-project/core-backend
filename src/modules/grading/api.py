from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.common.errors import bad_request
from src.db.session import get_db
from src.modules.analytics.repository import AnalyticsRepository
from src.modules.auth.api import get_current_user
from src.modules.auth.models import User
from src.modules.grading.repository import GradingRepository
from src.modules.grading.schemas import GradeQuizResponse
from src.modules.grading.service import GradingService
from src.modules.quizzes.repository import QuizRepository
from src.modules.quizzes.service import QuizService

router = APIRouter()


def get_grading_service(db: Session = Depends(get_db)) -> GradingService:
    return GradingService(
        grading_repository=GradingRepository(db),
        quiz_repository=QuizRepository(db),
        analytics_repository=AnalyticsRepository(db),
    )


def get_quiz_service(db: Session = Depends(get_db)) -> QuizService:
    return QuizService(QuizRepository(db))


@router.post("/{quiz_id}/attempts/{attempt_id}/grade", response_model=GradeQuizResponse, include_in_schema=False)
async def grade_attempt_compat(
    quiz_id: int,
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    quiz_service: QuizService = Depends(get_quiz_service),
    grading_service: GradingService = Depends(get_grading_service),
):
    attempt = quiz_service.get_attempt_by_id(attempt_id, current_user.id)
    if attempt.quiz_id != quiz_id:
        raise bad_request(
            f"Attempt with id {attempt_id} belongs to quiz with id {attempt.quiz_id}, not quiz with id {quiz_id}",
            error_code="QUIZ_ATTEMPT_MISMATCH",
            resource="attempt",
            resource_id=attempt_id,
            extra={"quiz_id": quiz_id, "actual_quiz_id": attempt.quiz_id},
        )
    result = grading_service.grade_quiz(attempt.quiz_id, current_user.id, attempt_id=attempt_id)
    return GradeQuizResponse(
        attempt_id=result.attempt_id,
        quiz_id=result.quiz_id,
        graded=True,
        total_score=float(result.total_score),
        max_score=float(result.max_score),
        percentage_score=float(result.percentage_score),
    )
