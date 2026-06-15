from datetime import datetime

from pydantic import BaseModel

from src.modules.topics.schemas import TopicBulkUpsertResult


class CourseRead(BaseModel):
    id: int
    code: str
    slug: str
    title: str
    description: str | None
    level: str | None
    semester_id: int | None
    semester: str | None
    active_compact_version: int | None = None

    model_config = {"from_attributes": True}


class CourseCreate(BaseModel):
    code: str
    title: str
    description: str | None = None
    level: str | None = None
    semester_id: int


class CourseUpdate(BaseModel):
    code: str | None = None
    title: str | None = None
    description: str | None = None
    level: str | None = None
    semester_id: int | None = None


class CourseCompactRead(BaseModel):
    id: int
    course_id: int
    version: int
    slug: str
    title: str
    file_type: str
    file_size: int
    text_extraction_status: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseCompactUploadRead(CourseCompactRead):
    imported_topics: TopicBulkUpsertResult | None = None
