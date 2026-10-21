from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import FacilityFaculty, Program
from backend.schemas.facility_faculty import FacilityFacultyResponse, FacilityFacultyCreate, FacilityFacultyUpdate


async def create_facility_faculty(session: AsyncSession, data: FacilityFacultyCreate) -> FacilityFacultyResponse:
    existing = await session.get(FacilityFaculty, data.staff_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Facility Faculty already exists",
        )
    program = await session.get(Program, data.program_id)
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    new_facility_faculty = FacilityFaculty(
        staff_id=data.staff_id,
        name=data.name,
        program_id=data.program_id,
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create Facility Faculty due to duplicate or invalid data",
        )
    await session.refresh(new_facility_faculty)
    return FacilityFacultyResponse.model_validate(new_facility_faculty)


async def get_all_facility_faculty(session: AsyncSession) -> list[FacilityFacultyResponse]:
    result = await session.execute(select(FacilityFaculty))
    facility_faculties = result.scalars().all()
    return [FacilityFacultyResponse.model_validate(facility_faculty) for facility_faculty in facility_faculties]


async def find_facility_faculty_by_id(session: AsyncSession, staff_id: str) -> FacilityFacultyResponse:
    facility_faculty = await session.get(FacilityFaculty, staff_id)
    if not facility_faculty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility Faculty not found")
    return FacilityFacultyResponse.model_validate(facility_faculty)


async def delete_facility_faculty(session: AsyncSession, staff_id: str) -> None:
    facility_faculty = await session.get(FacilityFaculty, staff_id)
    if not facility_faculty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility Faculty not found")
    await session.delete(facility_faculty)
    await session.commit()


async def update_facility_faculty(session: AsyncSession, staff_id: str, data: FacilityFacultyUpdate) -> FacilityFacultyResponse:
    faculty = await session.get(FacilityFaculty, staff_id)
    if not faculty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility Faculty not found")

    update_data = data.model_dump(exclude_unset=True)

    if "program_id" in update_data:
        program = await session.get(Program, update_data["program_id"])
        if not program:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Program not found",
            )

    for field, value in update_data.items():
        setattr(faculty, field, value)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not update Facility Faculty due to invalid data",
        )
    await session.refresh(faculty)
    return FacilityFacultyResponse.model_validate(faculty)