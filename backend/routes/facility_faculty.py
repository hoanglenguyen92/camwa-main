from typing import List

from fastapi import APIRouter

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOnly
from backend.helpers.response_wrapper import ApiResponse
from backend.schemas.facility_faculty import FacilityFacultyResponse, FacilityFacultyCreate, FacilityFacultyUpdate
from backend.services import facility_faculty_service

router = APIRouter(
    prefix="/facility-faculty",
    tags=["Facility Faculty"],
)


@router.post("/", response_model=ApiResponse[FacilityFacultyResponse], status_code=201)
async def create_faculty(
    session: AsyncSessionDep,
    data: FacilityFacultyCreate,
    _: AdminOnly = None,
):
    result = await facility_faculty_service.create_facility_faculty(session, data)
    return ApiResponse(
        message="Faculty created successfully",
        meta_data=result
    )


@router.get("/", response_model=ApiResponse[List[FacilityFacultyResponse]])
async def get_all_faculties(
    session: AsyncSessionDep,
    _: AdminOnly = None,
):
    result = await facility_faculty_service.get_all_facility_faculty(session)
    return ApiResponse(
        message="Faculties retrieved successfully",
        meta_data=result
    )


@router.get("/{staff_id}", response_model=ApiResponse[FacilityFacultyResponse])
async def get_faculty(
    session: AsyncSessionDep,
    staff_id: str,
    _: AdminOnly = None,
):
    result = await facility_faculty_service.find_facility_faculty_by_id(session, staff_id)
    return ApiResponse(
        message="Faculty retrieved successfully",
        meta_data=result
    )


@router.put("/{staff_id}", response_model=ApiResponse[FacilityFacultyResponse])
async def update_faculty(
        session: AsyncSessionDep,
        staff_id: str,
        data: FacilityFacultyUpdate,
        _: AdminOnly = None,
):
    result = await facility_faculty_service.update_facility_faculty(session, staff_id, data)
    return ApiResponse(
        message="Faculty updated successfully",
        meta_data=result,
    )


@router.delete("/{staff_id}", response_model=ApiResponse[None])
async def delete_faculty(
        session: AsyncSessionDep,
        staff_id: str,
        _: AdminOnly = None,
):
    await facility_faculty_service.delete_facility_faculty(session, staff_id)
    return ApiResponse(
        message="Faculty deleted successfully",
        meta_data=None
    )