from fastapi import APIRouter

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOnly
from backend.helpers.response_wrapper import ApiResponse
from backend.schemas.semester import SemesterResponse, SemesterCreate, SemesterUpdate
from backend.services import semester_service

router = APIRouter(
    prefix="/semester",
    tags=["Semester"],
)

@router.post("/", response_model=ApiResponse[SemesterResponse], status_code=201)
async def create_semester(
        session: AsyncSessionDep,
        data: SemesterCreate,
        _: AdminOnly = None
):
    semester = await semester_service.create_semester(session, data)
    return ApiResponse(
        message="Semester created successfully",
        meta_data=semester
    )


@router.get("/", response_model=ApiResponse[list[SemesterResponse]])
async def get_all_semester(
        session: AsyncSessionDep
):
    semesters = await semester_service.get_all_semester(session)
    return ApiResponse(
        message="Semesters retrieved successfully",
        meta_data=semesters
    )


@router.get("/current", response_model=ApiResponse[SemesterResponse])
async def get_current_semester(
        session: AsyncSessionDep
):
    semester = await semester_service.get_current_semester(session)
    return ApiResponse(
        message="Current semester retrieved successfully",
        meta_data=semester
    )


@router.get("/{sem_id}", response_model=ApiResponse[SemesterResponse])
async def get_semester_by_id(
        session: AsyncSessionDep,
        sem_id: str
):
    semester = await semester_service.find_semester_by_id(session, sem_id)
    return ApiResponse(
        message="Semester retrieved successfully",
        meta_data=semester
    )


@router.put("/{sem_id}", response_model=ApiResponse[SemesterResponse])
async def update_semester(
        session: AsyncSessionDep,
        sem_id: str,
        data: SemesterUpdate,
        _: AdminOnly = None
):
    semester = await semester_service.update_semester(session, sem_id, data)
    return ApiResponse(
        message="Semester updated successfully",
        meta_data=semester
    )


@router.delete("/{sem_id}", response_model=ApiResponse[None])
async def delete_semester(
        session: AsyncSessionDep,
        sem_id: str,
        _: AdminOnly = None
):
    await semester_service.delete_semester(session, sem_id)
    return ApiResponse(
        message="Semester deleted successfully",
        meta_data=None
    )


