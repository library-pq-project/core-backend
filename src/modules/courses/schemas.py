from pydantic import BaseModel


class CourseRead(BaseModel):
    id: int
    code: str
    slug: str
    title: str
    description: str | None
    level: str | None
    semester: str | None

    model_config = {"from_attributes": True}
