from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session
from typing import Literal

from src.db.session import get_db
from src.modules.auth.api import get_current_user, require_admin
from src.modules.auth.models import User
from src.modules.questions.repository import QuestionRepository
from src.modules.questions.schemas import (
    BulkImportResult,
    BulkQuestionImportRequest,
    QuestionCreate,
    QuestionImportJobRead,
    QuestionRead,
    QuestionUpdate,
)
from src.modules.questions.service import QuestionService
from src.modules.topics.repository import TopicRepository

router = APIRouter()


def get_question_service(db: Session = Depends(get_db)) -> QuestionService:
    return QuestionService(QuestionRepository(db), TopicRepository(db))


@router.get("", response_model=list[QuestionRead])
async def list_questions(
    assessment_id: int | None = Query(default=None),
    course_id: int | None = Query(default=None),
    topic_id: int | None = Query(default=None),
    year: int | None = Query(default=None),
    question_type: str | None = Query(default=None),
    source_type: Literal["actual", "ai_generated"] | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: QuestionService = Depends(get_question_service),
):
    return service.list_questions(
        course_id=course_id,
        assessment_id=assessment_id,
        topic_id=topic_id,
        year=year,
        question_type=question_type,
        source_type=source_type,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
async def create_question(
    payload: QuestionCreate,
    service: QuestionService = Depends(get_question_service),
    _=Depends(require_admin),
):
    return service.create_question(payload)


@router.post("/bulk", response_model=BulkImportResult, status_code=status.HTTP_201_CREATED)
async def bulk_import_questions_json(
    payload: BulkQuestionImportRequest,
    current_user: User = Depends(get_current_user),
    service: QuestionService = Depends(get_question_service),
    _=Depends(require_admin),
):
    return service.bulk_import_from_json(payload=payload, user_id=current_user.id)


@router.post("/bulk-upload", response_model=BulkImportResult, status_code=status.HTTP_201_CREATED)
async def bulk_import_questions_upload(
    file: UploadFile = File(...),
    import_mode: Literal["objective", "theory", "mixed"] = Form("mixed"),
    default_course_id: int | None = Form(default=None),
    default_assessment_id: int | None = Form(default=None),
    default_source_type: Literal["actual", "ai_generated"] = Form("actual"),
    auto_categorize_topics: bool = Form(True),
    draft_theory_without_solution: bool = Form(False),
    current_user: User = Depends(get_current_user),
    service: QuestionService = Depends(get_question_service),
    _=Depends(require_admin),
):
    content = await file.read()
    return service.bulk_import_from_file(
        file_name=file.filename or "questions.csv",
        content=content,
        user_id=current_user.id,
        import_mode=import_mode,
        default_course_id=default_course_id,
        default_assessment_id=default_assessment_id,
        default_source_type=default_source_type,
        auto_categorize_topics=auto_categorize_topics,
        draft_theory_without_solution=draft_theory_without_solution,
    )


@router.get("/import-jobs", response_model=list[QuestionImportJobRead])
async def list_question_import_jobs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: QuestionService = Depends(get_question_service),
):
    return service.list_import_jobs(user_id=current_user.id, skip=skip, limit=limit)


@router.get("/import-jobs/{job_id}", response_model=QuestionImportJobRead)
async def get_question_import_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    service: QuestionService = Depends(get_question_service),
):
    return service.get_import_job(job_id=job_id, user_id=current_user.id)


@router.get("/{question_id}", response_model=QuestionRead)
async def get_question(question_id: int, service: QuestionService = Depends(get_question_service)):
    return service.get_question(question_id)


@router.get("/{question_id}/options", response_model=list[dict])
async def get_question_options(
    question_id: int,
    include_correct: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    service: QuestionService = Depends(get_question_service),
):
    question = service.get_question(question_id)
    allow_correct = include_correct and current_user.role == "admin"
    output = []
    for option in sorted(question.options, key=lambda item: item.position):
        item = {
            "id": option.id,
            "option_text": option.option_text,
            "position": option.position,
        }
        if allow_correct:
            item["is_correct"] = option.is_correct
        output.append(item)
    return output


@router.put("/{question_id}", response_model=QuestionRead)
async def update_question(
    question_id: int,
    payload: QuestionUpdate,
    service: QuestionService = Depends(get_question_service),
    _=Depends(require_admin),
):
    return service.update_question(question_id, payload)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    service: QuestionService = Depends(get_question_service),
    _=Depends(require_admin),
):
    service.delete_question(question_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
