from pydantic import BaseModel


class TopicRead(BaseModel):
    id: int
    course_id: int
    name: str
    slug: str
    description: str | None

    model_config = {"from_attributes": True}
