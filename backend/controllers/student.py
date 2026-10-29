from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOrFA, AdminOrFAOrAC, AdminOrFAOrStudent, AllAuthenticated
from backend.core.policies import ensure_module_access, ensure_program_write, ensure_student_access, student_scope
from backend.helpers.http import SetLocation, read_upload
from backend.helpers.pagination import Page, PageDep
from backend.models import Student
from backend.schemas.student import StudentCreate, StudentImageCreate, StudentResponse, StudentUpdate
from backend.services import attendance_service, student_service

router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


@router.get("", response_model=Page[StudentResponse])
async def list_students(
    session: AsyncSessionDep,
    page: PageDep,
    user: AdminOrFAOrAC,
    program_id: Optional[str] = None,
    intake: Optional[int] = None,
):
    return await student_service.list_students(session, page, student_scope(user, Student.student_id), program_id, intake)


@router.post("", response_model=StudentResponse, status_code=201)
async def create_student(session: AsyncSessionDep, data: StudentCreate, user: AdminOrFA, location: SetLocation):
    ensure_program_write(user, data.program_id)
    student = await student_service.create_student(session, data)
    location(student.student_id)
    return student


@router.post("/imports")
async def import_students(session: AsyncSessionDep, user: AdminOrFA, file: UploadFile = File(...)):
    contents = await read_upload(file, ".xlsx", ".xls")
    return await student_service.create_multiple_student_from_excel(
        session, contents, None if user.is_admin else user.program_id
    )


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(session: AsyncSessionDep, student_id: str, user: AllAuthenticated):
    return await ensure_student_access(user, session, student_id)


@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student(session: AsyncSessionDep, student_id: str, data: StudentUpdate, user: AdminOrFA):
    if not user.is_admin:
        # An FA may also claim a student that has no program yet.
        student = await session.get(Student, student_id)
        if student is None or student.program_id not in (None, user.program_id):
            raise HTTPException(status_code=404, detail="Student not found")
        if "program_id" in data.model_fields_set:
            ensure_program_write(user, data.program_id)
    return await student_service.update_student(session, student_id, data)


@router.delete("/{student_id}", status_code=204)
async def delete_student(session: AsyncSessionDep, student_id: str, user: AdminOrFA):
    await ensure_student_access(user, session, student_id)
    await student_service.delete_student(session, student_id)


@router.get("/{student_id}/attendance-summary")
async def get_student_attendance_summary(session: AsyncSessionDep, student_id: str, user: AdminOrFAOrAC):
    await ensure_student_access(user, session, student_id)
    return await student_service.get_student_modules_with_attendance_rate(session, student_id)


@router.get("/{student_id}/exam-eligibility")
async def get_student_exam_eligibility(session: AsyncSessionDep, student_id: str, user: AllAuthenticated):
    await ensure_student_access(user, session, student_id)
    return await student_service.get_student_exam_eligibility_status(session, student_id)


@router.get("/{student_id}/modules/{module_id}/exam-eligibility")
async def get_student_module_exam_eligibility(
    session: AsyncSessionDep, student_id: str, module_id: str, user: AllAuthenticated
):
    await ensure_student_access(user, session, student_id)
    await ensure_module_access(user, session, module_id)
    return await attendance_service.check_exam_eligibility(session, student_id, module_id)


@router.post("/{student_id}/images", status_code=201)
async def create_student_image(
    session: AsyncSessionDep, student_id: str, data: StudentImageCreate, user: AdminOrFA, location: SetLocation
):
    await ensure_student_access(user, session, student_id)
    result = await student_service.create_student_image(session, student_id, data.image_path)
    location(result["image"]["image_id"])
    return result


@router.get("/{student_id}/images/{image_id}")
async def get_student_image(session: AsyncSessionDep, student_id: str, image_id: int, user: AdminOrFAOrStudent):
    await ensure_student_access(user, session, student_id)
    return await student_service.get_student_image_file(session, student_id, image_id)
