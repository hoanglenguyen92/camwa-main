from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOrFA, AllAuthenticated
from backend.core.policies import ensure_program_write
from backend.helpers.http import SetLocation, read_upload
from backend.helpers.pagination import Page, PageDep
from backend.schemas.lecturer import LecturerCreate, LecturerResponse, LecturerUpdate
from backend.services import lecturer_service

router = APIRouter(
    prefix="/lecturers",
    tags=["Lecturers"],
)


@router.get("", response_model=Page[LecturerResponse])
async def list_lecturers(session: AsyncSessionDep, page: PageDep, _: AllAuthenticated, program_id: Optional[str] = None):
    return await lecturer_service.list_lecturers(session, page, program_id)


@router.post("", response_model=LecturerResponse, status_code=201)
async def create_lecturer(session: AsyncSessionDep, data: LecturerCreate, user: AdminOrFA, location: SetLocation):
    ensure_program_write(user, data.program_id)
    lecturer = await lecturer_service.create_lecturer(session, data)
    location(lecturer.lecturer_id)
    return lecturer


@router.post("/imports")
async def import_lecturers(session: AsyncSessionDep, user: AdminOrFA, file: UploadFile = File(...)):
    contents = await read_upload(file, ".xlsx")
    return await lecturer_service.create_multiple_lecturers_from_excel(
        session, contents, None if user.is_admin else user.program_id
    )


@router.get("/{lecturer_id}", response_model=LecturerResponse)
async def get_lecturer(session: AsyncSessionDep, lecturer_id: str, _: AllAuthenticated):
    return await lecturer_service.get_lecturer(session, lecturer_id)


@router.patch("/{lecturer_id}", response_model=LecturerResponse)
async def update_lecturer(session: AsyncSessionDep, lecturer_id: str, data: LecturerUpdate, user: AdminOrFA):
    lecturer = await lecturer_service.get_lecturer(session, lecturer_id)
    ensure_program_write(user, lecturer.program_id)
    if not user.is_admin and "program_id" in data.model_fields_set:
        raise HTTPException(status_code=403, detail="Only ADMIN moves a lecturer between programs")
    return await lecturer_service.update_lecturer(session, lecturer_id, data)


@router.delete("/{lecturer_id}", status_code=204)
async def delete_lecturer(session: AsyncSessionDep, lecturer_id: str, user: AdminOrFA):
    lecturer = await lecturer_service.get_lecturer(session, lecturer_id)
    ensure_program_write(user, lecturer.program_id)
    await lecturer_service.delete_lecturer(session, lecturer_id)
