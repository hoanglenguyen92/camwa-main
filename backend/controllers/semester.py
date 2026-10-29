from fastapi import APIRouter

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOnly, AllAuthenticated
from backend.helpers.http import SetLocation
from backend.helpers.pagination import Page, PageDep, page_of
from backend.schemas.semester import SemesterCreate, SemesterResponse, SemesterUpdate
from backend.services import semester_service

router = APIRouter(
    prefix="/semesters",
    tags=["Semesters"],
)


@router.get("", response_model=Page[SemesterResponse])
async def list_semesters(session: AsyncSessionDep, page: PageDep, _: AllAuthenticated):
    return page_of(await semester_service.get_all_semester(session), page)


@router.post("", response_model=SemesterResponse, status_code=201)
async def create_semester(session: AsyncSessionDep, data: SemesterCreate, _: AdminOnly, location: SetLocation):
    semester = await semester_service.create_semester(session, data)
    location(semester.sem_id)
    return semester


@router.get("/current", response_model=SemesterResponse)
async def get_current_semester(session: AsyncSessionDep, _: AllAuthenticated):
    return await semester_service.get_current_semester(session)


@router.get("/{sem_id}", response_model=SemesterResponse)
async def get_semester(session: AsyncSessionDep, sem_id: str, _: AllAuthenticated):
    return await semester_service.find_semester_by_id(session, sem_id)


@router.patch("/{sem_id}", response_model=SemesterResponse)
async def update_semester(session: AsyncSessionDep, sem_id: str, data: SemesterUpdate, _: AdminOnly):
    return await semester_service.update_semester(session, sem_id, data)


@router.delete("/{sem_id}", status_code=204)
async def delete_semester(session: AsyncSessionDep, sem_id: str, _: AdminOnly):
    await semester_service.delete_semester(session, sem_id)
