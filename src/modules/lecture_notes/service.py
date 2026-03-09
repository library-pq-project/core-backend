import os
import uuid

from docx import Document
from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader

from src.common.utils import generate_slug
from src.core.config import settings
from src.modules.lecture_notes.models import LectureNote
from src.modules.lecture_notes.repository import LectureNoteRepository


class LectureNoteService:
    SUPPORTED_TYPES = {"pdf", "docx", "txt"}

    def __init__(self, repository: LectureNoteRepository):
        self.repository = repository
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    def _extract_text(self, file_path: str, extension: str) -> tuple[str | None, str]:
        try:
            if extension == "txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                    return file.read(), "completed"

            if extension == "pdf":
                reader = PdfReader(file_path)
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
                return text, "completed"

            if extension == "docx":
                doc = Document(file_path)
                text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
                return text, "completed"

            return None, "failed"
        except Exception:
            return None, "failed"

    async def upload(
        self, *, user_id: int, course_id: int, title: str, upload_file: UploadFile
    ) -> LectureNote:
        extension = upload_file.filename.split(".")[-1].lower() if upload_file.filename else ""
        if extension not in self.SUPPORTED_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")

        unique_name = f"{uuid.uuid4().hex}.{extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

        content = await upload_file.read()
        with open(file_path, "wb") as file:
            file.write(content)

        extracted_text, extraction_status = self._extract_text(file_path, extension)

        lecture_note = LectureNote(
            user_id=user_id,
            course_id=course_id,
            title=title,
            slug=generate_slug(title),
            original_file_name=upload_file.filename or unique_name,
            stored_file_name=unique_name,
            file_path=file_path,
            file_type=extension,
            file_size=len(content),
            extracted_text=extracted_text,
            text_extraction_status=extraction_status,
        )
        return self.repository.create(lecture_note)

    def list_my_notes(self, user_id: int, *, skip: int, limit: int) -> list[LectureNote]:
        return self.repository.list_by_user(user_id, skip=skip, limit=limit)

    def get_my_note(self, lecture_note_id: int, user_id: int) -> LectureNote:
        lecture_note = self.repository.get_for_user(lecture_note_id, user_id)
        if not lecture_note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecture note not found")
        return lecture_note

    def delete_my_note(self, lecture_note_id: int, user_id: int) -> None:
        lecture_note = self.get_my_note(lecture_note_id, user_id)
        if os.path.exists(lecture_note.file_path):
            os.remove(lecture_note.file_path)
        self.repository.delete(lecture_note)
