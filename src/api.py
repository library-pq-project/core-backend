from fastapi import APIRouter

from src.modules.academic.api import router as academic_router
from src.modules.ai_generation.api import router as ai_generation_router
from src.modules.analytics.api import router as analytics_router
from src.modules.auth.api import router as auth_router
from src.modules.courses.api import router as courses_router
from src.modules.grading.api import router as grading_router
from src.modules.lecture_notes.api import router as lecture_notes_router
from src.modules.questions.api import router as questions_router
from src.modules.quizzes.api import router as quizzes_router
from src.modules.topics.api import router as topics_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(academic_router, prefix="/academic", tags=["Academic"])
api_router.include_router(courses_router, prefix="/courses", tags=["Courses"])
api_router.include_router(topics_router, prefix="/topics", tags=["Topics"])
api_router.include_router(lecture_notes_router, prefix="/lecture-notes", tags=["Lecture Notes"])
api_router.include_router(questions_router, prefix="/questions", tags=["Questions"])
api_router.include_router(ai_generation_router, prefix="/ai", tags=["AI Generation"])
api_router.include_router(quizzes_router, prefix="/quizzes", tags=["Quizzes"])
api_router.include_router(grading_router, prefix="/quizzes", tags=["Grading"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
