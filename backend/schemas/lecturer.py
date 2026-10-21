from typing import Optional

from pydantic import BaseModel


class LecturerResponse(BaseModel):
    lecturer_id: str
    name: str
    program_id: str
    model_config = {"from_attributes": True}


class LecturerCreate(LecturerResponse):
    pass


class LecturerUpdate(BaseModel):
    name: Optional[str] = None
    program_id: Optional[str] = None