from pydantic import BaseModel, Field


class TopicRead(BaseModel):
    id: int
    course_id: int
    name: str
    slug: str
    description: str | None

    model_config = {"from_attributes": True}


class TopicCreate(BaseModel):
    course_id: int
    name: str
    description: str | None = None


class TopicUpdate(BaseModel):
    course_id: int | None = None
    name: str | None = None
    description: str | None = None


class ImportRowError(BaseModel):
    row_number: int
    errors: list[str]


class TopicBulkRow(BaseModel):
    course_id: int
    name: str
    description: str | None = None


class TopicBulkUpsertRequest(BaseModel):
    rows: list[TopicBulkRow] = Field(default_factory=list)


class TopicBulkUpsertResult(BaseModel):
    created_count: int
    updated_count: int
    skipped_count: int
    errors: list[ImportRowError]
    topic_ids: list[int]
