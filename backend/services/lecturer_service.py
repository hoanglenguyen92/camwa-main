import io
from typing import List

import openpyxl
from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Lecturer, Program
from backend.schemas.lecturer import LecturerCreate, LecturerResponse, LecturerUpdate


async def create_lecturer(session: AsyncSession, data: LecturerCreate) -> LecturerResponse:

    existing = await session.get(Lecturer, data.lecturer_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lecturer already exists",
        )
    program = await session.get(Program, data.program_id)
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    new_lecturer = Lecturer(
        lecturer_id=data.lecturer_id,
        name=data.name,
        program_id=data.program_id,
    )
    session.add(new_lecturer)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create lecturer due to duplicate or invalid data",
        )
    await session.refresh(new_lecturer)
    return LecturerResponse.model_validate(new_lecturer)


async def get_all_lecturers(session: AsyncSession) -> List[LecturerResponse]:
    result = await session.execute(select(Lecturer))
    lecturers = result.scalars().all()
    return [LecturerResponse.model_validate(lecturer) for lecturer in lecturers]


async def find_lecturer_by_id(session: AsyncSession, lecturer_id: str) -> LecturerResponse:
    lecturer = await session.get(Lecturer, lecturer_id)
    if not lecturer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lecturer not found: {lecturer_id}")
    return LecturerResponse.model_validate(lecturer)


async def delete_lecturer(session: AsyncSession, lecturer_id: str) -> None:
    lecturer = await session.get(Lecturer, lecturer_id)
    if not lecturer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lecturer not found: {lecturer_id}")
    await session.delete(lecturer)
    await session.commit()


async def update_lecturer(session: AsyncSession, lecturer_id: str, lecturer_update: LecturerUpdate) -> LecturerResponse:
    lecturer = await session.get(Lecturer, lecturer_id)
    if not lecturer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lecturer not found: {lecturer_id}")

    update_data = lecturer_update.model_dump(exclude_unset=True)

    if "program_id" in update_data:
        program = await session.get(Program, update_data["program_id"])
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Program not found",
            )

    for field, value in update_data.items():
        setattr(lecturer, field, value)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not update lecturer due to invalid data",
        )
    await session.refresh(lecturer)
    return LecturerResponse.model_validate(lecturer)


async def _process_excel(session: AsyncSession, file_contents: bytes):
    workbook = openpyxl.load_workbook(io.BytesIO(file_contents))
    sheet = workbook.active

    successful = []
    failed = []

    for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        lecturer_id = str(row[0]).strip() if len(row) > 0 and row[0] else None
        name = str(row[2]).strip() if len(row) > 2 and row[2] else None
        program_id = str(row[3]).strip() if len(row) > 3 and row[3] else None

        if not lecturer_id or not name or not program_id:
            failed.append({
                "row": row_index,
                "lecturer_id": lecturer_id,
                "name": name,
                "program_id": program_id,
                "error": "Missing required fields",
            })
            continue

        # Check duplicates
        existing = await session.get(Lecturer, lecturer_id)
        if existing:
            failed.append({
                "row": row_index,
                "lecturer_id": lecturer_id,
                "name": name,
                "program_id": program_id,
                "error": "Lecturer already exists",
            })
            continue

        program = await session.get(Program, program_id)
        if not program:
            failed.append({
                "row": row_index,
                "lecturer_id": lecturer_id,
                "name": name,
                "program_id": program_id,
                "error": "Program not found",
            })
            continue

        new_lecturer = Lecturer(
            lecturer_id=lecturer_id,
            name=name,
            program_id=program_id,
        )
        session.add(new_lecturer)
        successful.append({
            "lecturer_id": lecturer_id,
            "name": name,
            "program_id": program_id
        })

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Could not import lecturers: {exc.orig}",
        )
    return {"successful": successful, "failed": failed}


async def create_multiple_lecturers_from_excel(session: AsyncSession, file_contents: bytes):
    return await _process_excel(session, file_contents)