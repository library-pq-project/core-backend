from pydantic import BaseModel


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
