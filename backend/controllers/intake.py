from fastapi import APIRouter

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOnly, AllAuthenticated
from backend.helpers.http import SetLocation
from backend.helpers.pagination import Page, PageDep, page_of
from backend.schemas.intake import IntakeCreate, IntakeResponse, IntakeUpdate
from backend.services import intake_service

router = APIRouter(
    prefix="/intakes",
    tags=["Intakes"],
)


@router.get("", response_model=Page[IntakeResponse])
async def list_intakes(session: AsyncSessionDep, page: PageDep, _: AllAuthenticated):
    return page_of(await intake_service.get_all_intakes(session), page)


@router.post("", response_model=IntakeResponse, status_code=201)
async def create_intake(session: AsyncSessionDep, data: IntakeCreate, _: AdminOnly, location: SetLocation):
    intake = await intake_service.create_intake(session, data)
    location(intake.year)
    return intake


@router.get("/{year}", response_model=IntakeResponse)
async def get_intake(session: AsyncSessionDep, year: int, _: AllAuthenticated):
    return await intake_service.find_intake_by_year(session, year)


@router.patch("/{year}", response_model=IntakeResponse)
async def update_intake(session: AsyncSessionDep, year: int, data: IntakeUpdate, _: AdminOnly):
    return await intake_service.update_intake(session, year, data)


@router.delete("/{year}", status_code=204)
async def delete_intake(session: AsyncSessionDep, year: int, _: AdminOnly):
    await intake_service.delete_intake(session, year)
