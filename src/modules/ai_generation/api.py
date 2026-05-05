from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.ai_generation.repository import AIQuestionGenerationRepository
from src.modules.ai_generation.schemas import AIQuestionGenerationCreate, AIQuestionGenerationResponse
from src.modules.ai_generation.service import AIQuestionGenerationService
from src.modules.ai_generation.providers import GeminiQuestionGenerator
from src.modules.auth.api import get_current_user
from src.modules.auth.models import User
from src.modules.courses.repository import CourseRepository
from src.modules.lecture_notes.repository import LectureNoteRepository
from src.modules.topics.repository import TopicRepository

router = APIRouter()


def get_ai_generation_service(db: Session = Depends(get_db)) -> AIQuestionGenerationService:
    return AIQuestionGenerationService(
        repository=AIQuestionGenerationRepository(db),
        lecture_note_repository=LectureNoteRepository(db),
        course_repository=CourseRepository(db),
        topic_repository=TopicRepository(db),
        ai_client=GeminiQuestionGenerator(),
    )


@router.post("/question-generation", response_model=AIQuestionGenerationResponse, status_code=status.HTTP_201_CREATED)
async def generate_questions(
    payload: AIQuestionGenerationCreate,
    current_user: User = Depends(get_current_user),
    service: AIQuestionGenerationService = Depends(get_ai_generation_service),
):
    (
        fingerprint,
        questions,
        reused_count,
        generated_count,
        model_name,
        estimated_input_tokens,
        estimated_output_tokens,
    ) = service.generate_or_reuse(payload, current_user.id)
    return AIQuestionGenerationResponse(
        fingerprint=fingerprint,
        reused_count=reused_count,
        generated_count=generated_count,
        model_name=model_name,
        estimated_input_tokens=estimated_input_tokens,
        estimated_output_tokens=estimated_output_tokens,
        questions=questions,
    )
