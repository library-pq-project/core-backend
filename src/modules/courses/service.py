from docx import Document
from fastapi import HTTPException, status
from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy.exc import IntegrityError

from src.common.errors import bad_request, conflict, not_found
from src.common.utils import generate_slug
from src.modules.courses.ai_topic_extractor import CourseTopicExtractor, GeminiCourseTopicExtractor
from src.modules.courses.models import Course, CourseCompact
from src.modules.courses.repository import CourseRepository
from src.modules.courses.schemas import CourseCreate, CourseUpdate
from src.modules.lecture_notes.storage import FileStorageProvider, build_storage_provider
from src.modules.topics.repository import TopicRepository
from src.modules.topics.schemas import TopicBulkRow, TopicBulkUpsertRequest, TopicBulkUpsertResult
from src.modules.topics.service import TopicService


class CourseService:
    SUPPORTED_COMPACT_TYPES = {"pdf", "docx", "txt", "md", "json"}

    def __init__(
        self,
        repository: CourseRepository,
        storage_provider: FileStorageProvider | None = None,
        topic_repository: TopicRepository | None = None,
        topic_extractor: CourseTopicExtractor | None = None,
    ):
        self.repository = repository
        self._storage_provider = storage_provider
        self.topic_repository = topic_repository or TopicRepository(repository.db)
        self.topic_service = TopicService(self.topic_repository)
        self.topic_extractor = topic_extractor or GeminiCourseTopicExtractor()

    @property
    def storage_provider(self) -> FileStorageProvider:
        if self._storage_provider is None:
            self._storage_provider = build_storage_provider()
        return self._storage_provider

    def list_courses(
        self,
        *,
        skip: int,
        limit: int,
        semester_id: int | None = None,
        level: str | None = None,
        program_id: int | None = None,
        academic_session_id: int | None = None,
        code: str | None = None,
        search: str | None = None,
    ) -> list[Course]:
        courses = self.repository.list(
            skip=skip,
            limit=limit,
            semester_id=semester_id,
            level=level,
            program_id=program_id,
            academic_session_id=academic_session_id,
            code=code,
            search=search,
        )
        for course in courses:
            active_compact = self.repository.get_active_compact(course.id)
            setattr(course, "active_compact_version", active_compact.version if active_compact else None)
        return courses

    def get_course(self, course_id: int) -> Course:
        course = self.repository.get(course_id)
        if not course:
            raise not_found("course", course_id)
        active_compact = self.repository.get_active_compact(course.id)
        setattr(course, "active_compact_version", active_compact.version if active_compact else None)
        return course

    def get_course_by_slug(self, course_slug: str) -> Course:
        course = self.repository.get_by_slug(course_slug)
        if not course:
            raise not_found("course", course_slug)
        active_compact = self.repository.get_active_compact(course.id)
        setattr(course, "active_compact_version", active_compact.version if active_compact else None)
        return course

    def create_course(self, payload: CourseCreate) -> Course:
        semester = self.repository.get_semester(payload.semester_id)
        if semester is None:
            raise not_found("semester", payload.semester_id)

        course = Course(
            code=payload.code,
            slug=generate_slug(payload.code),
            title=payload.title,
            description=payload.description,
            level=payload.level,
            semester_id=semester.id,
            semester=semester.name,
        )
        try:
            return self.repository.create(course)
        except IntegrityError as exc:
            raise conflict(
                f"Course with code {payload.code} already exists",
                error_code="COURSE_ALREADY_EXISTS",
                resource="course",
            ) from exc

    def update_course(self, course_id: int, payload: CourseUpdate) -> Course:
        course = self.get_course(course_id)
        updates = payload.model_dump(exclude_unset=True)

        if "code" in updates:
            course.code = updates["code"]
            course.slug = generate_slug(updates["code"])
        if "title" in updates:
            course.title = updates["title"]
        if "description" in updates:
            course.description = updates["description"]
        if "level" in updates:
            course.level = updates["level"]
        if "semester_id" in updates:
            semester_id = updates["semester_id"]
            if semester_id is None:
                course.semester_id = None
                course.semester = None
            else:
                semester = self.repository.get_semester(semester_id)
                if semester is None:
                    raise not_found("semester", semester_id)
                course.semester_id = semester.id
                course.semester = semester.name

        try:
            return self.repository.save(course)
        except IntegrityError as exc:
            raise conflict(
                f"Course with code {course.code} could not be updated because it conflicts with existing course data",
                error_code="COURSE_CONFLICT",
                resource="course",
                resource_id=course_id,
            ) from exc

    def delete_course(self, course_id: int) -> None:
        course = self.get_course(course_id)
        self.repository.delete(course)

    def _extract_text_from_bytes(self, content: bytes, extension: str) -> tuple[str | None, str]:
        try:
            if extension in {"txt", "md", "json"}:
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

    def _build_topic_rows_from_compact(self, *, course_id: int, compact_text: str, course_title: str) -> list[TopicBulkRow]:
        topic_names = self.topic_extractor.extract_topics(course_title=course_title, compact_text=compact_text)
        rows: list[TopicBulkRow] = []
        seen: set[str] = set()
        for item in topic_names:
            cleaned = " ".join(item.split()).strip()
            if not cleaned:
                continue
            normalized = cleaned.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            rows.append(TopicBulkRow(course_id=course_id, name=cleaned, description="Imported from course compact"))
        return rows

    def import_topics_from_compact(self, *, course_id: int, compact_id: int) -> TopicBulkUpsertResult:
        self.get_course(course_id)
        compact = self.repository.get_compact(compact_id)
        if compact is None or compact.course_id != course_id:
            raise not_found("compact", compact_id)
        if compact.text_extraction_status != "completed" or not compact.extracted_text:
            raise bad_request(
                f"Compact with id {compact_id} does not have extracted text available for topic import",
                error_code="COMPACT_TEXT_NOT_READY",
                resource="compact",
                resource_id=compact_id,
            )

        course = self.get_course(course_id)
        rows = self._build_topic_rows_from_compact(
            course_id=course_id,
            compact_text=compact.extracted_text,
            course_title=course.title,
        )
        if not rows:
            return TopicBulkUpsertResult(
                created_count=0,
                updated_count=0,
                skipped_count=1,
                errors=[],
                topic_ids=[],
            )
        return self.topic_service.bulk_upsert_topics(TopicBulkUpsertRequest(rows=rows))

    def upload_course_compact(
        self,
        *,
        course_id: int,
        title: str,
        upload_file: UploadFile,
        admin_user_id: int,
    ) -> tuple[CourseCompact, TopicBulkUpsertResult | None]:
        course = self.get_course(course_id)
        extension = upload_file.filename.split(".")[-1].lower() if upload_file.filename else ""
        if extension not in self.SUPPORTED_COMPACT_TYPES:
            raise bad_request(
                f"Unsupported compact file type '{extension or 'unknown'}'",
                error_code="UNSUPPORTED_COMPACT_TYPE",
            )

        content = upload_file.file.read()
        if not content:
            raise bad_request("Compact file is empty", error_code="EMPTY_COMPACT_FILE")

        stored = self.storage_provider.save(
            original_name=upload_file.filename or f"compact.{extension}",
            content=content,
        )
        extracted_text, extraction_status = self._extract_text_from_bytes(content, extension)
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
        compact = self.repository.create_compact(compact)

        imported_topics = None
        if extraction_status == "completed" and extracted_text:
            try:
                imported_topics = self.import_topics_from_compact(course_id=course.id, compact_id=compact.id)
            except Exception:
                imported_topics = None
        return compact, imported_topics

    def list_course_compacts(self, course_id: int, *, active_only: bool, skip: int, limit: int) -> list[CourseCompact]:
        self.get_course(course_id)
        return self.repository.list_compacts(course_id, active_only=active_only, skip=skip, limit=limit)

    def get_active_compact(self, course_id: int) -> CourseCompact:
        self.get_course(course_id)
        compact = self.repository.get_active_compact(course_id)
        if compact is None:
            raise not_found("active_compact", course_id)
        return compact

    def activate_compact(self, course_id: int, compact_id: int) -> CourseCompact:
        self.get_course(course_id)
        compact = self.repository.get_compact(compact_id)
        if compact is None or compact.course_id != course_id:
            raise not_found("compact", compact_id)
        self.repository.deactivate_compacts(course_id)
        compact.is_active = True
        return self.repository.save(compact)
