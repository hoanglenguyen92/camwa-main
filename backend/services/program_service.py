from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Program, Student, Lecturer, Module
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


async def assign_student_to_program(
    session: AsyncSession,
    program_id: str,
    student_id: str,
) -> dict:
    await _ensure_program_exists(session, program_id)

    student = await session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student.program_id = program_id
    await session.commit()

    return {"message": "Student assigned to program successfully"}


async def assign_lecturer_to_program(
    session: AsyncSession,
    program_id: str,
    lecturer_id: str,
) -> dict:
    await _ensure_program_exists(session, program_id)

    lecturer = await session.get(Lecturer, lecturer_id)
    if not lecturer:
        raise HTTPException(status_code=404, detail="Lecturer not found")

    lecturer.program_id = program_id
    await session.commit()

    return {"message": "Lecturer assigned to program successfully"}


async def assign_module_to_program(
    session: AsyncSession,
    program_id: str,
    module_id: str,
) -> dict:
    await _ensure_program_exists(session, program_id)

    module = await session.get(Module, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    module.program_id = program_id
    await session.commit()

    return {"message": "Module assigned to program successfully"}


async def view_modules_in_program(session: AsyncSession, program_id: str) -> list[dict]:
    await _ensure_program_exists(session, program_id)
    result = await session.execute(
        select(Module).where(Module.program_id == program_id)
    )
    modules = result.scalars().all()
    return [
        {
            "module_id": module.module_id,
            "name": module.name,
            "lecturer_id": module.lecturer_id,
            "program_id": module.program_id,
            "intake": module.intake,
            "semester_id": module.semester_id,
            "camera_path": module.camera_path,
        }
        for module in modules
    ]


async def view_lecturers_in_program(session: AsyncSession, program_id: str) -> list[dict]:
    await _ensure_program_exists(session, program_id)
    result = await session.execute(
        select(Lecturer).where(Lecturer.program_id == program_id)
    )
    lecturers = result.scalars().all()
    return [
        {
            "lecturer_id": lecturer.lecturer_id,
            "name": lecturer.name,
            "program_id": lecturer.program_id,
        }
        for lecturer in lecturers
    ]


async def view_students_in_program(session: AsyncSession, program_id: str) -> list[dict]:
    await _ensure_program_exists(session, program_id)
    result = await session.execute(
        select(Student).where(Student.program_id == program_id)
    )
    students = result.scalars().all()
    return [
        {
            "student_id": student.student_id,
            "name": student.name,
            "map_location": student.map_location,
            "program_id": student.program_id,
            "intake": student.intake,
        }
        for student in students
    ]