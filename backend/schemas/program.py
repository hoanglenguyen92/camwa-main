from typing import Optional

from pydantic import BaseModel


class ProgramResponse(BaseModel):
    program_id: str
    name: Optional[str] = None
    model_config = {"from_attributes": True}


class ProgramCreate(ProgramResponse):
    pass


class ProgramUpdate(BaseModel):
    name: Optional[str] = None