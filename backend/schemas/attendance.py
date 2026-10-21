from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from backend.models.enums import AttendanceStatus, RequestStatus


class AttendanceResponse(BaseModel):
    attendance_id: int
    student_id: str
    module_id: str
    attendance_status: AttendanceStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class AttendanceCreate(BaseModel):
    student_id: str
    module_id: str
    attendance_status: AttendanceStatus


class AttendanceUpdate(BaseModel):
    attendance_status: AttendanceStatus


class AttendanceRequestCreate(BaseModel):
    attendance_id: int
    student_id: str
    module_id: str
    proposed_status: AttendanceStatus
    reason: Optional[str]


class CorrectionApproval(BaseModel):
    approved_status: AttendanceStatus
    processed_by: str


class AttendanceRequestResponse(BaseModel):
    request_id: int
    attendance_id: int
    student_id: str
    module_id: str
    request_status: RequestStatus
    proposed_status: AttendanceStatus
    approved_status: Optional[AttendanceStatus] = None
    reason: Optional[str] = None
    processed_by: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class ExamEligibilityResponse(BaseModel):
    student_id: str
    module_id: str
    attendance_rate: float
    is_eligible: bool
    model_config = {"from_attributes": True}