import os
import re

from docx import Document
from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader

from src.common.utils import generate_slug
from src.core.config import settings
from src.modules.lecture_notes.models import LectureNote
from src.modules.lecture_notes.repository import LectureNoteRepository
from src.modules.lecture_notes.storage import FileStorageProvider, build_storage_provider


class LectureNoteService:
    SUPPORTED_TYPES = {"pdf", "docx", "txt"}

    def __init__(self, repository: LectureNoteRepository, storage_provider: FileStorageProvider | None = None):
        self.repository = repository
        self._storage_provider = storage_provider

    @property
    def storage_provider(self) -> FileStorageProvider:
        if self._storage_provider is None:
            self._storage_provider = build_storage_provider()
        return self._storage_provider

    def _tokenize(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) >= 3}

    def _compute_relevance(
        self,
        *,
        course_id: int,
        extracted_text: str | None,
        extraction_status: str,
    ) -> tuple[float | None, str, str | None]:
        if extraction_status != "completed" or not extracted_text:
            return None, "failed", "Text extraction failed; relevance could not be computed."

        context = self.repository.get_course_relevance_context(course_id)
        course = context["course"]
        if course is None:
            return None, "failed", "Course not found for relevance computation."

        reference_tokens: set[str] = set()
        reference_tokens.update(self._tokenize(course.code))
        reference_tokens.update(self._tokenize(course.title))
        if course.description:
            reference_tokens.update(self._tokenize(course.description))
        for topic in context["topics"]:
            reference_tokens.update(self._tokenize(topic.name))
            if topic.description:
                reference_tokens.update(self._tokenize(topic.description))
        compact = context["compact"]
        if compact and compact.extracted_text:
            reference_tokens.update(self._tokenize(compact.extracted_text[:5000]))

        note_tokens = self._tokenize(extracted_text[:25000])
        if not reference_tokens or not note_tokens:
            return 0.0, "warning", "Insufficient tokens to compute relevance."

        overlap = len(reference_tokens.intersection(note_tokens))
        score = overlap / max(len(reference_tokens), 1)
        status_value = "accepted" if score >= settings.LECTURE_NOTE_RELEVANCE_THRESHOLD else "warning"
        reason = (
            "Lecture note appears relevant to selected course."
            if status_value == "accepted"
            else "Lecture note relevance is low compared to course compact/topics."
        )
        return score, status_value, reason

    def _extract_text_from_bytes(self, content: bytes, extension: str) -> tuple[str | None, str]:
        try:
            if extension == "txt":
                return content.decode("utf-8", errors="ignore"), "completed"

            if extension == "pdf":
                from io import BytesIO

                reader = PdfReader(BytesIO(content))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
                return text, "completed"

            if extension == "docx":
                from io import BytesIO

                doc = Document(BytesIO(content))
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

        content = await upload_file.read()
        if len(content) > settings.MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max allowed is {settings.MAX_UPLOAD_FILE_SIZE_MB}MB",
            )
        stored = self.storage_provider.save(
            original_name=upload_file.filename or f"upload.{extension}",
            content=content,
        )

        extracted_text, extraction_status = self._extract_text_from_bytes(content, extension)
        relevance_score, relevance_status, relevance_reason = self._compute_relevance(
            course_id=course_id,
            extracted_text=extracted_text,
            extraction_status=extraction_status,
        )
        if (
            relevance_status == "warning"
            and settings.LECTURE_NOTE_RELEVANCE_MODE.lower().strip() == "reject"
        ):
            self.storage_provider.delete(key=stored.key, path=stored.path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lecture note relevance score is below policy threshold for this course.",
            )

        lecture_note = LectureNote(
            user_id=user_id,
            course_id=course_id,
            title=title,
            slug=generate_slug(title),
            original_file_name=upload_file.filename or stored.key,
            stored_file_name=stored.key,
            storage_provider=stored.provider,
            storage_bucket=stored.bucket,
            storage_key=stored.key,
            file_path=stored.path,
            file_type=extension,
            file_size=len(content),
            extracted_text=extracted_text,
            text_extraction_status=extraction_status,
            relevance_score=relevance_score,
            relevance_status=relevance_status,
            relevance_reason=relevance_reason,
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
        if lecture_note.storage_key or lecture_note.file_path:
            if lecture_note.storage_provider != "local" or (
                lecture_note.file_path and os.path.exists(lecture_note.file_path)
            ):
                self.storage_provider.delete(
                    key=lecture_note.storage_key or lecture_note.stored_file_name,
                    path=lecture_note.file_path,
                )
        self.repository.delete(lecture_note)
