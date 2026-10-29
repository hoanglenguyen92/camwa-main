from typing import Optional

from fastapi import APIRouter, File, UploadFile

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOrFA, AdminOrFAOrLecturer, AllAuthenticated
from backend.core.policies import ensure_module_access, ensure_row_access, row_scope
from backend.helpers.http import SetLocation, read_upload
from backend.helpers.pagination import Page, PageDep
from backend.models import ModuleRegistration
from backend.schemas.module_registration import (
    ModuleRegistrationCreate,
    ModuleRegistrationResponse,
    ModuleRegistrationUpdate,
)
from backend.services import module_registration_service

router = APIRouter(
    prefix="/module-registrations",
    tags=["ModuleRegistrations"],
)


async def _registration_in_reach(user, session, module_reg_id: int) -> ModuleRegistration:
    return await ensure_row_access(
        user, session, ModuleRegistration, ModuleRegistration.module_reg_id, module_reg_id, "Registration not found"
    )


@router.get("", response_model=Page[ModuleRegistrationResponse])
async def list_module_registrations(
    session: AsyncSessionDep,
    page: PageDep,
    user: AllAuthenticated,
    student_id: Optional[str] = None,
    module_id: Optional[str] = None,
    lecturer_id: Optional[str] = None,
):
    scope = row_scope(user, ModuleRegistration.module_id, ModuleRegistration.student_id)
    return await module_registration_service.list_registrations(session, page, scope, student_id, module_id, lecturer_id)


@router.post("", response_model=ModuleRegistrationResponse, status_code=201)
async def create_module_registration(
    session: AsyncSessionDep, data: ModuleRegistrationCreate, user: AdminOrFA, location: SetLocation
):
    await ensure_module_access(user, session, data.module_id)
    record = await module_registration_service.create_registration(session, data)
    location(record.module_reg_id)
    return record


@router.post("/imports")
async def import_module_registrations(session: AsyncSessionDep, user: AdminOrFA, file: UploadFile = File(...)):
    contents = await read_upload(file, ".xlsx", ".xls")
    return await module_registration_service.create_multiple_module_registration_from_excel(
        session, contents, None if user.is_admin else user.program_id
    )


@router.get("/{module_reg_id}", response_model=ModuleRegistrationResponse)
async def get_module_registration(session: AsyncSessionDep, module_reg_id: int, user: AdminOrFAOrLecturer):
    return await _registration_in_reach(user, session, module_reg_id)


@router.patch("/{module_reg_id}", response_model=ModuleRegistrationResponse)
async def update_module_registration(
    session: AsyncSessionDep, module_reg_id: int, data: ModuleRegistrationUpdate, user: AdminOrFA
):
    row = await _registration_in_reach(user, session, module_reg_id)
    if data.module_id:
        await ensure_module_access(user, session, data.module_id)
    return await module_registration_service.update_registration(session, row, data)


@router.delete("/{module_reg_id}", status_code=204)
async def delete_module_registration(session: AsyncSessionDep, module_reg_id: int, user: AdminOrFA):
    row = await _registration_in_reach(user, session, module_reg_id)
    await module_registration_service.delete_registration(session, row)
