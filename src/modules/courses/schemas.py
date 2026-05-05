from datetime import datetime

from pydantic import BaseModel


class CourseRead(BaseModel):
    id: int
    code: str
    slug: str
    title: str
    description: str | None
    level: str | None
    semester: str | None
    active_compact_version: int | None = None

    model_config = {"from_attributes": True}


class CourseCreate(BaseModel):
    code: str
    title: str
    description: str | None = None
    level: str | None = None
    semester: str | None = None


class CourseUpdate(BaseModel):
    code: str | None = None
    title: str | None = None
    description: str | None = None
    level: str | None = None
    semester: str | None = None


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
