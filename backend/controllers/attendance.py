from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOrFA, AllAuthenticated
from backend.core.policies import ensure_module_access, ensure_row_access, row_scope
from backend.helpers.http import SetLocation, read_upload
from backend.helpers.pagination import Page, PageDep
from backend.models import Attendance
from backend.models.enums import AccountRole
from backend.schemas.attendance import AttendanceCreate, AttendanceResponse, AttendanceUpdate
from backend.services import attendance_service

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"],
)


@router.get("", response_model=Page[AttendanceResponse])
async def list_attendance(
    session: AsyncSessionDep,
    page: PageDep,
    user: AllAuthenticated,
    student_id: Optional[str] = None,
    module_id: Optional[str] = None,
):
    scope = row_scope(user, Attendance.module_id, Attendance.student_id)
    return await attendance_service.list_attendance(session, page, scope, student_id, module_id)


@router.post("", response_model=AttendanceResponse, status_code=201)
async def submit_attendance(session: AsyncSessionDep, data: AttendanceCreate, user: AllAuthenticated, location: SetLocation):
    if user.acting == AccountRole.STUDENT:
        if data.student_id != user.camwa_id:
            raise HTTPException(status_code=403, detail="Students can only submit their own attendance")
    else:
        await ensure_module_access(user, session, data.module_id)
    attendance = await attendance_service.submit_attendance(session, data)
    location(attendance.attendance_id)
    return attendance


@router.post("/imports")
async def import_attendance(session: AsyncSessionDep, user: AdminOrFA, file: UploadFile = File(...)):
    contents = await read_upload(file, ".xlsx", ".xls")
    return await attendance_service.import_attendance_from_excel(
        session, contents, None if user.is_admin else user.program_id
    )


async def _attendance_in_reach(user, session, attendance_id: int) -> Attendance:
    return await ensure_row_access(
        user, session, Attendance, Attendance.attendance_id, attendance_id, "Attendance not found"
    )


@router.patch("/{attendance_id}", response_model=AttendanceResponse)
async def update_attendance(session: AsyncSessionDep, attendance_id: int, data: AttendanceUpdate, user: AdminOrFA):
    attendance = await _attendance_in_reach(user, session, attendance_id)
    return await attendance_service.update_attendance(session, attendance, data)


@router.delete("/{attendance_id}", status_code=204)
async def delete_attendance(session: AsyncSessionDep, attendance_id: int, user: AdminOrFA):
    attendance = await _attendance_in_reach(user, session, attendance_id)
    await attendance_service.delete_attendance(session, attendance)
