from typing import Optional

from pydantic import BaseModel


class StudentResponse(BaseModel):
    student_id: str
    name: Optional[str] = None
    map_location: Optional[str] = None
    program_id: Optional[str] = None
    intake: Optional[int] = None
    model_config = {"from_attributes": True}


class StudentCreate(StudentResponse):
    pass


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    map_location: Optional[str] = None
    program_id: Optional[str] = None
    intake: Optional[int] = None


class StudentImageCreate(BaseModel):
    image_path: Optional[str] = None