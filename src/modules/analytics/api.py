from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.analytics.repository import AnalyticsRepository
from src.modules.analytics.schemas import AnalyticsOverview, AttemptTopicMetricRead, TopicPerformanceRead
from src.modules.analytics.service import AnalyticsService
from src.modules.auth.api import get_current_user
from src.modules.auth.models import User

router = APIRouter()


def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(AnalyticsRepository(db))


@router.get("/me/overview", response_model=AnalyticsOverview)
async def get_overview(
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return service.get_overview(current_user.id)


@router.get("/me/topic-performance", response_model=list[TopicPerformanceRead])
async def get_topic_performance(
    course_id: int | None = Query(default=None),
    academic_session_id: int | None = Query(default=None),
    topic_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return service.get_topic_performance(
        user_id=current_user.id,
        course_id=course_id,
        academic_session_id=academic_session_id,
        topic_id=topic_id,
    )


@router.get("/me/attempt-topic-metrics", response_model=list[AttemptTopicMetricRead])
async def list_attempt_topic_metrics(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return service.list_attempt_metrics(current_user.id, skip=skip, limit=limit)
