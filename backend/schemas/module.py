from typing import Optional

from pydantic import BaseModel


class ModuleResponse(BaseModel):
    module_id: str
    name: str
    lecturer_id: str
    program_id: str
    intake: int
    semester_id: str
    camera_path: Optional[str] = None
    model_config = {"from_attributes": True}


class ModuleCreate(ModuleResponse):
    pass


class ModuleUpdate(BaseModel):
    name: Optional[str] = None
    lecturer_id: Optional[str] = None
    program_id: Optional[str] = None
    intake: Optional[int] = None
    semester_id: Optional[str] = None
    camera_path: Optional[str] = None


class CameraPathUpdate(BaseModel):
    camera_path: str