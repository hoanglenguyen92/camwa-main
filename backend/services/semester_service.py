from datetime import datetime, timezone, date
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


from backend.models import Semester
from backend.schemas.semester import SemesterCreate, SemesterResponse, SemesterUpdate


async def create_semester(session: AsyncSession, data: SemesterCreate) -> SemesterResponse:
    sem_id = data.sem_id or str(uuid4())
    existing = await session.get(Semester, sem_id)
    if existing:
        raise HTTPException(status_code=409, detail="Semester already exists")
    semester = Semester(
        sem_id=sem_id,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    session.add(semester)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Could not create semester")
    await session.refresh(semester)
    return SemesterResponse.model_validate(semester)


async def get_all_semester(session: AsyncSession) -> list[SemesterResponse]:
    result = await session.execute(select(Semester).order_by(Semester.start_date.desc()))
    semesters = result.scalars().all()
    return [SemesterResponse.model_validate(semester) for semester in semesters]


async def find_semester_by_id(session: AsyncSession, sem_id: str) -> SemesterResponse:
    semester = await session.get(Semester, sem_id)
    if not semester:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")
    return SemesterResponse.model_validate(semester)


async def update_semester(
    session: AsyncSession,
    sem_id: str,
    data: SemesterUpdate,
) -> SemesterResponse:
    semester = await session.get(Semester, sem_id)
    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found")
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No changes provided")
    for field, value in update_data.items():
        setattr(semester, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Could not update semester")
    await session.refresh(semester)
    return SemesterResponse.model_validate(semester)


async def delete_semester(session: AsyncSession, sem_id: str) -> None:
    semester = await session.get(Semester, sem_id)
    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found")
    try:
        await session.delete(semester)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete semester because it is used by other records",
        )


async def get_current_semester(session: AsyncSession) -> SemesterResponse:
    today = date.today()
    result = await session.execute(
        select(Semester)
        .where(Semester.start_date <= today)
        .where(Semester.end_date >= today)
        .order_by(Semester.start_date.desc())
    )
    semester = result.scalars().first()
    if not semester:
        raise HTTPException(status_code=404, detail="No current semester found")
    return SemesterResponse.model_validate(semester)