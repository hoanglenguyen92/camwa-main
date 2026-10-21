from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from backend.models import Intake
from backend.schemas.intake import IntakeCreate, IntakeResponse, IntakeUpdate


async def create_intake(session: AsyncSession, data: IntakeCreate) -> IntakeResponse:

    existing = await session.get(Intake, data.year)
    if existing:
        raise HTTPException(status_code=409, detail="Intake already exists")

    intake = Intake(
        year=data.year,
    )
    session.add(intake)
    await session.commit()
    await session.refresh(intake)
    return IntakeResponse.model_validate(intake)


async def get_all_intakes(session: AsyncSession) -> list[IntakeResponse]:
    result = await session.execute(select(Intake).order_by(Intake.year.desc()))
    intakes = result.scalars().all()
    return [IntakeResponse.model_validate(intake) for intake in intakes]


async def find_intake_by_year(session: AsyncSession, year: int) -> IntakeResponse:
    intake = await session.get(Intake, year)
    if not intake:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake not found")
    return IntakeResponse.model_validate(intake)


async def update_intake(session: AsyncSession, year: int, data: IntakeUpdate) -> IntakeResponse:

    if data.year != year:
        existing = await session.get(Intake, data.year)
        if existing:
            raise HTTPException(status_code=409, detail="Target intake year already exists")
    
    intake = await session.get(Intake, year)
    if not intake:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake not found")

    update_data = data.model_dump()

    for field, value in update_data.items():
        setattr(intake, field, value)

    await session.commit()
    await session.refresh(intake)
    return IntakeResponse.model_validate(intake)


async def delete_intake(session: AsyncSession, year: int) -> None:
    intake = await session.get(Intake, year)
    if not intake:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake not found")
    await session.delete(intake)
    await session.commit()