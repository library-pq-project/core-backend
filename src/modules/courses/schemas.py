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
