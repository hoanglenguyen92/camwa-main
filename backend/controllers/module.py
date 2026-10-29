from typing import List, Optional

from fastapi import APIRouter, File, UploadFile

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOnly, AdminOrFA, AdminOrFAOrAC, AdminOrFAOrLecturerOrAC, AllAuthenticated
from backend.core.policies import ensure_module_access, ensure_program_write, module_scope
from backend.helpers.http import SetLocation, read_upload
from backend.helpers.pagination import Page, PageDep
from backend.models import Module, ModuleRegistration
from backend.schemas.attendance import ExamEligibilityResponse
from backend.schemas.module import CameraPathUpdate, ModuleCreate, ModuleResponse, ModuleUpdate
from backend.services import attendance_service, module_registration_service, module_service

router = APIRouter(
    prefix="/modules",
    tags=["Modules"],
)


@router.get("", response_model=Page[ModuleResponse])
async def list_modules(
    session: AsyncSessionDep,
    page: PageDep,
    user: AdminOrFAOrAC,
    program_id: Optional[str] = None,
    semester_id: Optional[str] = None,
    lecturer_id: Optional[str] = None,
):
    return await module_service.list_modules(
        session, page, module_scope(user, Module.module_id), program_id, semester_id, lecturer_id
    )


@router.post("", response_model=ModuleResponse, status_code=201)
async def create_module(session: AsyncSessionDep, data: ModuleCreate, user: AdminOrFA, location: SetLocation):
    ensure_program_write(user, data.program_id)
    module = await module_service.create_module(session, data)
    location(module.module_id)
    return module


@router.post("/imports")
async def import_modules(session: AsyncSessionDep, user: AdminOrFA, file: UploadFile = File(...)):
    contents = await read_upload(file, ".xlsx", ".xls")
    return await module_service.create_multiple_module_from_excel(
        session, contents, None if user.is_admin else user.program_id
    )


@router.post("/bulk-deletions")
async def delete_modules(session: AsyncSessionDep, _: AdminOnly, file: UploadFile = File(...)):
    contents = await read_upload(file, ".xlsx")
    return await module_service.delete_multiple_modules_from_excel(session, contents)


@router.get("/attendance-summary")
async def get_modules_attendance_summary(session: AsyncSessionDep, user: AdminOrFAOrAC):
    return await module_registration_service.get_all_modules_with_student_count_and_attendance_rate(
        session, module_scope(user, ModuleRegistration.module_id)
    )


@router.get("/{module_id}", response_model=ModuleResponse)
async def get_module(session: AsyncSessionDep, module_id: str, user: AllAuthenticated):
    return await ensure_module_access(user, session, module_id)


@router.patch("/{module_id}", response_model=ModuleResponse)
async def update_module(session: AsyncSessionDep, module_id: str, data: ModuleUpdate, _: AdminOnly):
    return await module_service.update_module(session, module_id, data)


@router.delete("/{module_id}", status_code=204)
async def delete_module(session: AsyncSessionDep, module_id: str, _: AdminOnly):
    await module_service.delete_module(session, module_id)


@router.get("/{module_id}/camera-path")
async def get_camera_path(session: AsyncSessionDep, module_id: str, _: AdminOnly):
    return await module_service.get_camera_path(session, module_id)


@router.put("/{module_id}/camera-path")
async def set_camera_path(session: AsyncSessionDep, module_id: str, data: CameraPathUpdate, _: AdminOnly):
    return await module_service.set_camera_path(session, module_id, data.camera_path)


@router.get("/{module_id}/exam-eligibility", response_model=List[ExamEligibilityResponse])
async def get_module_exam_eligibility(session: AsyncSessionDep, module_id: str, user: AdminOrFAOrLecturerOrAC):
    await ensure_module_access(user, session, module_id)
    return await attendance_service.get_exam_eligibility_by_module(session, module_id)
