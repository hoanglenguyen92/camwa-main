from fastapi import APIRouter

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOnly
from backend.helpers.response_wrapper import ApiResponse
from backend.schemas.intake import IntakeResponse, IntakeCreate, IntakeUpdate
from backend.services import intake_service

router = APIRouter(
    prefix="/intake",
    tags=["Intake"],
)

@router.post("/", response_model=ApiResponse[IntakeResponse], status_code=201)
async def create_intake(
        session: AsyncSessionDep,
        data: IntakeCreate,
        _: AdminOnly = None
):
    intake = await intake_service.create_intake(session, data)
    return ApiResponse(
        message="Intake created successfully",
        meta_data=intake
    )


@router.get("/", response_model=ApiResponse[list[IntakeResponse]])
async def get_all_intakes(session: AsyncSessionDep):
    intakes = await intake_service.get_all_intakes(session)
    return ApiResponse(
        message="Intakes retrieved successfully",
        meta_data=intakes
    )


@router.get("/{year}", response_model=ApiResponse[IntakeResponse])
async def get_intake_by_year(session: AsyncSessionDep, year: int):
    intake = await intake_service.find_intake_by_year(session, year)
    return ApiResponse(
        message="Intake retrieved successfully",
        meta_data=intake
    )


@router.put("/{year}", response_model=ApiResponse[IntakeResponse])
async def update_intake(
        session: AsyncSessionDep,
        year: int,
        data: IntakeUpdate,
        _: AdminOnly = None
):
    intake = await intake_service.update_intake(session, year, data)
    return ApiResponse(
        message="Intake updated successfully",
        meta_data=intake
    )


@router.delete("/{year}", response_model=ApiResponse[None])
async def delete_intake(
        session: AsyncSessionDep,
        year: int,
        _: AdminOnly = None
):
    await intake_service.delete_intake(session, year)
    return ApiResponse(
        message="Intake deleted successfully",
        meta_data=None
    )