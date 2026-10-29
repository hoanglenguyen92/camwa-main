from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Program
from backend.schemas.program import ProgramCreate, ProgramResponse, ProgramUpdate


async def _ensure_program_exists(session: AsyncSession, program_id: str) -> Program:
    program = await session.get(Program, program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


async def create_program(session: AsyncSession, data: ProgramCreate) -> ProgramResponse:
    existing = await session.get(Program, data.program_id)
    if existing:
        raise HTTPException(status_code=409, detail="Program already exists")

    program = Program(
        program_id=data.program_id,
        name=data.name,
    )
    session.add(program)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Could not create program")

    await session.refresh(program)
    return ProgramResponse.model_validate(program)


async def get_all_programs(session: AsyncSession) -> List[ProgramResponse]:
    result = await session.execute(select(Program))
    programs = result.scalars().all()
    return [ProgramResponse.model_validate(program) for program in programs]


async def find_program_by_id(session: AsyncSession, program_id: str) -> ProgramResponse:
    program = await session.get(Program, program_id)
    if not program:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return ProgramResponse.model_validate(program)


async def delete_program(session: AsyncSession, program_id: str) -> None:
    program = await _ensure_program_exists(session, program_id)

    try:
        await session.delete(program)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete program because it is used by other records",
        )


async def update_program(
    session: AsyncSession,
    program_id: str,
    data: ProgramUpdate,
) -> ProgramResponse:
    program = await _ensure_program_exists(session, program_id)

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        return ProgramResponse.model_validate(program)

    for field, value in update_data.items():
        setattr(program, field, value)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Could not update program")

    await session.refresh(program)
    return ProgramResponse.model_validate(program)
