from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.modules.auth.api import get_current_user
from src.modules.auth.models import User
from src.modules.lecture_notes.repository import LectureNoteRepository
from src.modules.lecture_notes.schemas import LectureNoteRead
from src.modules.lecture_notes.service import LectureNoteService

router = APIRouter()


def get_lecture_note_service(db: Session = Depends(get_db)) -> LectureNoteService:
    return LectureNoteService(LectureNoteRepository(db))


@router.post("", response_model=LectureNoteRead, status_code=status.HTTP_201_CREATED)
async def upload_lecture_note(
    title: str = Form(...),
    course_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: LectureNoteService = Depends(get_lecture_note_service),
):
    return await service.upload(user_id=current_user.id, course_id=course_id, title=title, upload_file=file)


@router.get("", response_model=list[LectureNoteRead])
async def list_lecture_notes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: LectureNoteService = Depends(get_lecture_note_service),
):
    return service.list_my_notes(current_user.id, skip=skip, limit=limit)


@router.get("/{lecture_note_id}", response_model=LectureNoteRead)
async def get_lecture_note(
    lecture_note_id: int,
    current_user: User = Depends(get_current_user),
    service: LectureNoteService = Depends(get_lecture_note_service),
):
    return service.get_my_note(lecture_note_id, current_user.id)


@router.delete("/{lecture_note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lecture_note(
    lecture_note_id: int,
    current_user: User = Depends(get_current_user),
    service: LectureNoteService = Depends(get_lecture_note_service),
):
    service.delete_my_note(lecture_note_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
