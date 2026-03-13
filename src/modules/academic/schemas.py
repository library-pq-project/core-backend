from datetime import datetime

from pydantic import BaseModel


class AcademicSessionCreate(BaseModel):
    name: str


class AcademicSessionRead(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool

    model_config = {"from_attributes": True}


class SemesterCreate(BaseModel):
    name: str


class SemesterRead(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool

    model_config = {"from_attributes": True}


class ProgramCreate(BaseModel):
    code: str
    name: str
    description: str | None = None


class ProgramRead(BaseModel):
    id: int
    code: str
    name: str
    slug: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ActiveCalendarUpdate(BaseModel):
    academic_session_id: int
    semester_id: int


class ActiveCalendarRead(BaseModel):
    academic_session_id: int
    semester_id: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProgramCourseOfferingCreate(BaseModel):
    program_id: int
    course_id: int
    level: str
    academic_session_id: int
    semester_id: int


class ProgramCourseOfferingRead(BaseModel):
    id: int
    program_id: int
    course_id: int
    level: str
    academic_session_id: int
    semester_id: int

    model_config = {"from_attributes": True}


class AssessmentCreate(BaseModel):
    course_id: int
    academic_session_id: int
    semester_id: int | None = None
    assessment_type: str
    question_format: str
    year_label: str | None = None


class AssessmentRead(BaseModel):
    id: int
    course_id: int
    academic_session_id: int
    semester_id: int | None
    assessment_type: str
    question_format: str
    year_label: str | None
    slug: str

    model_config = {"from_attributes": True}
