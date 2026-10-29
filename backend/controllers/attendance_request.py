from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOrFA, AdminOrFAOrLecturerOrStudent, AdminOrFAOrStudent, StudentOnly
from backend.core.policies import ensure_row_access, row_scope
from backend.helpers.http import SetLocation
from backend.helpers.pagination import Page, PageDep
from backend.models import AttendanceRequest
from backend.models.enums import AccountRole, RequestStatus
from backend.schemas.attendance import AttendanceRequestCreate, AttendanceRequestResponse, CorrectionDecision
from backend.services import attendance_service

router = APIRouter(
    prefix="/attendance-requests",
    tags=["AttendanceRequests"],
)


async def _request_in_reach(user, session, request_id: int) -> AttendanceRequest:
    return await ensure_row_access(
        user, session, AttendanceRequest, AttendanceRequest.request_id, request_id, "Attendance request not found"
    )


@router.get("", response_model=Page[AttendanceRequestResponse])
async def list_attendance_requests(
    session: AsyncSessionDep,
    page: PageDep,
    user: AdminOrFAOrLecturerOrStudent,
    status: Optional[RequestStatus] = None,
    student_id: Optional[str] = None,
    module_id: Optional[str] = None,
):
    scope = row_scope(user, AttendanceRequest.module_id, AttendanceRequest.student_id)
    return await attendance_service.list_requests(session, page, scope, status, student_id, module_id)


@router.post("", response_model=AttendanceRequestResponse, status_code=201)
async def create_attendance_request(
    session: AsyncSessionDep,
    background_tasks: BackgroundTasks,
    data: AttendanceRequestCreate,
    user: StudentOnly,
    location: SetLocation,
):
    if data.student_id != user.camwa_id:
        raise HTTPException(status_code=403, detail="Students can only request corrections for their own attendance")
    req = await attendance_service.request_correction(session, background_tasks, data)
    location(req.request_id)
    return req


@router.get("/{request_id}", response_model=AttendanceRequestResponse)
async def get_attendance_request(session: AsyncSessionDep, request_id: int, user: AdminOrFAOrLecturerOrStudent):
    return await _request_in_reach(user, session, request_id)


@router.patch("/{request_id}", response_model=AttendanceRequestResponse)
async def decide_attendance_request(
    session: AsyncSessionDep,
    background_tasks: BackgroundTasks,
    request_id: int,
    decision: CorrectionDecision,
    user: AdminOrFA,
):
    req = await _request_in_reach(user, session, request_id)
    return await attendance_service.decide_correction(session, background_tasks, req, decision, user.camwa_id)


@router.delete("/{request_id}", status_code=204)
async def delete_attendance_request(session: AsyncSessionDep, request_id: int, user: AdminOrFAOrStudent):
    req = await _request_in_reach(user, session, request_id)
    if user.acting == AccountRole.STUDENT and req.request_status != RequestStatus.PENDING:
        raise HTTPException(status_code=409, detail="Only a pending request can be withdrawn")
    await attendance_service.delete_attendance_request(session, req)
