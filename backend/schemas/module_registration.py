from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class ModuleRegistrationResponse(BaseModel):
    module_reg_id: int
    student_id: str
    module_id: str
    lecturer_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class ModuleRegistrationCreate(BaseModel):
    student_id: str
    module_id: str
    lecturer_id: str


class ModuleRegistrationUpdate(BaseModel):
    student_id: Optional[str] = None
    module_id: Optional[str] = None
    lecturer_id: Optional[str] = None


class LecturerModuleStudentAttendanceItem(BaseModel):
    student_id: str
    student_name: str
    attendance_rate: float
    total_classes: int
    attended_classes: int


class LecturerModuleStudentsAttendance(BaseModel):
    module_id: str
    module_name: str
    students: List[LecturerModuleStudentAttendanceItem]


class LecturerStudentsAttendanceResponse(BaseModel):
    lecturer_id: str
    modules: List[LecturerModuleStudentsAttendance]