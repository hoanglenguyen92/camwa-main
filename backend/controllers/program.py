from fastapi import APIRouter, HTTPException

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOnly, AdminOrFAOrAC
from backend.helpers.http import SetLocation
from backend.helpers.pagination import Page, PageDep, page_of
from backend.schemas.program import ProgramCreate, ProgramResponse, ProgramUpdate
from backend.services import program_service

router = APIRouter(
    prefix="/programs",
    tags=["Programs"],
)


@router.get("", response_model=Page[ProgramResponse])
async def list_programs(session: AsyncSessionDep, page: PageDep, user: AdminOrFAOrAC):
    programs = await program_service.get_all_programs(session)
    if not user.is_admin:
        programs = [p for p in programs if p.program_id == user.program_id]
    return page_of(programs, page)


@router.post("", response_model=ProgramResponse, status_code=201)
async def create_program(session: AsyncSessionDep, data: ProgramCreate, _: AdminOnly, location: SetLocation):
    program = await program_service.create_program(session, data)
    location(program.program_id)
    return program


@router.get("/{program_id}", response_model=ProgramResponse)
async def get_program(session: AsyncSessionDep, program_id: str, user: AdminOrFAOrAC):
    if not user.is_admin and program_id != user.program_id:
        raise HTTPException(status_code=404, detail="Program not found")
    return await program_service.find_program_by_id(session, program_id)


@router.patch("/{program_id}", response_model=ProgramResponse)
async def update_program(session: AsyncSessionDep, program_id: str, data: ProgramUpdate, _: AdminOnly):
    return await program_service.update_program(session, program_id, data)


@router.delete("/{program_id}", status_code=204)
async def delete_program(session: AsyncSessionDep, program_id: str, _: AdminOnly):
    await program_service.delete_program(session, program_id)
