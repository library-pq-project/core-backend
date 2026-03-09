from datetime import datetime

from pydantic import BaseModel


class LectureNoteRead(BaseModel):
    id: int
    user_id: int
    course_id: int
    title: str
    slug: str
    original_file_name: str
    file_type: str
    file_size: int
    text_extraction_status: str
    created_at: datetime

    model_config = {"from_attributes": True}
