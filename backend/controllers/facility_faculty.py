from fastapi import APIRouter

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOnly
from backend.helpers.http import SetLocation
from backend.helpers.pagination import Page, PageDep, page_of
from backend.schemas.facility_faculty import FacilityFacultyCreate, FacilityFacultyResponse, FacilityFacultyUpdate
from backend.services import facility_faculty_service

router = APIRouter(
    prefix="/faculty-staff",
    tags=["FacultyStaff"],
)


@router.get("", response_model=Page[FacilityFacultyResponse])
async def list_faculty_staff(session: AsyncSessionDep, page: PageDep, _: AdminOnly):
    return page_of(await facility_faculty_service.get_all_facility_faculty(session), page)


@router.post("", response_model=FacilityFacultyResponse, status_code=201)
async def create_faculty_staff(
    session: AsyncSessionDep, data: FacilityFacultyCreate, _: AdminOnly, location: SetLocation
):
    staff = await facility_faculty_service.create_facility_faculty(session, data)
    location(staff.staff_id)
    return staff


@router.get("/{staff_id}", response_model=FacilityFacultyResponse)
async def get_faculty_staff(session: AsyncSessionDep, staff_id: str, _: AdminOnly):
    return await facility_faculty_service.find_facility_faculty_by_id(session, staff_id)


@router.patch("/{staff_id}", response_model=FacilityFacultyResponse)
async def update_faculty_staff(session: AsyncSessionDep, staff_id: str, data: FacilityFacultyUpdate, _: AdminOnly):
    return await facility_faculty_service.update_facility_faculty(session, staff_id, data)


@router.delete("/{staff_id}", status_code=204)
async def delete_faculty_staff(session: AsyncSessionDep, staff_id: str, _: AdminOnly):
    await facility_faculty_service.delete_facility_faculty(session, staff_id)
