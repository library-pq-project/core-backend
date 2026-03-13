from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.auth.api import get_current_user
from src.modules.auth.models import User
from src.modules.quizzes.repository import QuizRepository
from src.modules.quizzes.schemas import QuizAttemptQuestionRead
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
