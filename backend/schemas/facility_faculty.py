from typing import Optional

from pydantic import BaseModel


class FacilityFacultyResponse(BaseModel):
    staff_id: str
    name: str
    program_id: str
    model_config = {"from_attributes": True}


class FacilityFacultyCreate(FacilityFacultyResponse):
    pass


class FacilityFacultyUpdate(BaseModel):
    name: Optional[str] = None
    program_id: Optional[str] = None

