from fastapi import APIRouter, Depends
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


@router.post("/{quiz_id}/grade", response_model=GradeQuizResponse)
async def grade_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    service: GradingService = Depends(get_grading_service),
):
    result = service.grade_quiz(quiz_id, current_user.id)
    return GradeQuizResponse(
        quiz_id=result.quiz_id,
        graded=True,
        total_score=float(result.total_score),
        max_score=float(result.max_score),
        percentage_score=float(result.percentage_score),
    )
