from docx import Document
from fastapi import HTTPException, status
from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy.exc import IntegrityError

from src.common.utils import generate_slug
from src.modules.courses.models import Course, CourseCompact
from src.modules.courses.repository import CourseRepository
from src.modules.courses.schemas import CourseCreate, CourseUpdate
from src.modules.lecture_notes.storage import FileStorageProvider


class CourseService:
    SUPPORTED_COMPACT_TYPES = {"pdf", "docx", "txt", "md", "json"}

    def __init__(self, repository: CourseRepository, storage_provider: FileStorageProvider):
        self.repository = repository
        self.storage_provider = storage_provider

    def list_courses(self, *, skip: int, limit: int) -> list[Course]:
        courses = self.repository.list(skip=skip, limit=limit)
        for course in courses:
            active_compact = self.repository.get_active_compact(course.id)
            setattr(course, "active_compact_version", active_compact.version if active_compact else None)
        return courses

    def get_course(self, course_id: int) -> Course:
        course = self.repository.get(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        active_compact = self.repository.get_active_compact(course.id)
        setattr(course, "active_compact_version", active_compact.version if active_compact else None)
        return course

    def get_course_by_slug(self, course_slug: str) -> Course:
        course = self.repository.get_by_slug(course_slug)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        active_compact = self.repository.get_active_compact(course.id)
        setattr(course, "active_compact_version", active_compact.version if active_compact else None)
        return course

    def create_course(self, payload: CourseCreate) -> Course:
        course = Course(
            code=payload.code,
            slug=generate_slug(payload.code),
            title=payload.title,
            description=payload.description,
            level=payload.level,
            semester=payload.semester,
        )
        try:
            return self.repository.create(course)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Course with this code or slug already exists",
            ) from exc

    def update_course(self, course_id: int, payload: CourseUpdate) -> Course:
        course = self.get_course(course_id)
        updates = payload.model_dump(exclude_unset=True)

        if "code" in updates:
            course.code = updates["code"]
        if "title" in updates:
            course.slug = generate_slug(updates["title"])
        if "title" in updates:
            course.title = updates["title"]
        if "description" in updates:
            course.description = updates["description"]
        if "level" in updates:
            course.level = updates["level"]
        if "semester" in updates:
            course.semester = updates["semester"]

        try:
            return self.repository.save(course)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Course with this code or slug already exists",
            ) from exc

    def delete_course(self, course_id: int) -> None:
        course = self.get_course(course_id)
        self.repository.delete(course)

    def _extract_text(self, file_path: str, extension: str) -> tuple[str | None, str]:
        try:
            if extension in {"txt", "md", "json"}:
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

    def upload_course_compact(
        self,
        *,
        course_id: int,
        title: str,
        upload_file: UploadFile,
        admin_user_id: int,
    ) -> CourseCompact:
        course = self.get_course(course_id)
        extension = upload_file.filename.split(".")[-1].lower() if upload_file.filename else ""
        if extension not in self.SUPPORTED_COMPACT_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported compact file type")

        content = upload_file.file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Compact file is empty")

        stored = self.storage_provider.save(
            original_name=upload_file.filename or f"compact.{extension}",
            content=content,
        )
        extracted_text, extraction_status = self._extract_text(stored.path, extension)
        summary = (extracted_text or "")[:2000] if extraction_status == "completed" else None

        version = self.repository.get_next_compact_version(course_id)
        compact = CourseCompact(
            course_id=course.id,
            version=version,
            slug=generate_slug(f"{course.code}-compact-v{version}"),
            title=title,
            file_type=extension,
            file_size=len(content),
            storage_provider=stored.provider,
            storage_bucket=stored.bucket,
            storage_key=stored.key,
            file_path=stored.path,
            extracted_text=extracted_text,
            compact_summary=summary,
            taxonomy_text=None,
            key_terms_text=None,
            pitfalls_text=None,
            text_extraction_status=extraction_status,
            is_active=True,
            created_by_user_id=admin_user_id,
        )
        self.repository.deactivate_compacts(course_id)
        return self.repository.create_compact(compact)

    def list_course_compacts(self, course_id: int, *, active_only: bool, skip: int, limit: int) -> list[CourseCompact]:
        self.get_course(course_id)
        return self.repository.list_compacts(course_id, active_only=active_only, skip=skip, limit=limit)

    def get_active_compact(self, course_id: int) -> CourseCompact:
        self.get_course(course_id)
        compact = self.repository.get_active_compact(course_id)
        if compact is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active compact not found")
        return compact

    def activate_compact(self, course_id: int, compact_id: int) -> CourseCompact:
        self.get_course(course_id)
        compact = self.repository.get_compact(compact_id)
        if compact is None or compact.course_id != course_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compact not found")
        self.repository.deactivate_compacts(course_id)
        compact.is_active = True
        return self.repository.save(compact)
