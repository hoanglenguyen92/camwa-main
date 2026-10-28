from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOrFA, AdminOrFAOrLecturer, AllAuthenticated, AdminOrFAOrLecturerOrAC, LecturerOnly, \
    StudentOnly
from backend.helpers.response_wrapper import ApiResponse
from backend.schemas.module_registration import ModuleRegistrationResponse, ModuleRegistrationCreate, \
    ModuleRegistrationUpdate, LecturerStudentsAttendanceResponse
from backend.services import module_registration_service

router = APIRouter(
    prefix="/module-registrations",
    tags=["Module Registrations"]
)


def _ensure_student_self_access(user, student_id: str) -> None:
    if user.role == "STUDENT" and user.iam_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students can only access their own registrations",
        )


def _ensure_lecturer_self_access(user, lecturer_id: str) -> None:
    if user.role == "LECTURER" and user.iam_id != lecturer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lecturers can only access their own modules",
        )


@router.post("/", response_model=ApiResponse[ModuleRegistrationResponse], status_code=201)
async def create_module_registration(
        session: AsyncSessionDep,
        data: ModuleRegistrationCreate,
        _: AdminOrFA = None
):
    record = await module_registration_service.create_registration(session, data)
    return ApiResponse(
        message="Module registration created successfully",
        meta_data=record
    )


@router.post("/create-from-excel", response_model=ApiResponse)
async def import_module_registrations(
        session: AsyncSessionDep,
        file: UploadFile = File(...),
        _: AdminOrFA = None
):
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in [".xlsx", ".xls"]):
        raise HTTPException(status_code=400, detail="Invalid file type. Only Excel files are allowed.")

    contents = await file.read()
    result = await module_registration_service.create_multiple_module_registration_from_excel(session, contents)
    return ApiResponse(
        message="Modules imported successfully",
        meta_data=result
    )


@router.get("/", response_model=ApiResponse[List[ModuleRegistrationResponse]])
async def get_all_module_registrations(
        session: AsyncSessionDep,
        _: AdminOrFAOrLecturer = None
):
    records = await module_registration_service.get_all_registrations(session)
    return ApiResponse(
        message="Module registrations retrieved successfully",
        meta_data=records
    )


@router.get("/student/{student_id}", response_model=ApiResponse[List[ModuleRegistrationResponse]])
async def get_by_student(
        session: AsyncSessionDep,
        student_id: str,
        user: AllAuthenticated
):

    _ensure_student_self_access(user, student_id)

    rows = await module_registration_service.find_registrations_by_student_id(session, student_id)
    return ApiResponse(
        message="Student registrations retrieved successfully",
        meta_data=rows
    )


@router.get("/module/{module_id}", response_model=ApiResponse[List[ModuleRegistrationResponse]])
async def get_by_module(
        session: AsyncSessionDep,
        module_id: str,
        _: AdminOrFAOrLecturer = None
):
    rows = await module_registration_service.find_registrations_by_module_id(session, module_id)
    return ApiResponse(
        message="Module registrations retrieved successfully",
        meta_data=rows
    )


@router.get("/lecturer/{lecturer_id}", response_model=ApiResponse[list[dict]])
async def get_by_lecturer(
        session: AsyncSessionDep,
        lecturer_id: str,
        user: AdminOrFAOrLecturerOrAC
):
    _ensure_lecturer_self_access(user, lecturer_id)

    rows = await module_registration_service.get_lecturer_modules_with_student_count(session, lecturer_id)
    return ApiResponse(
        message="Lecturer modules retrieved successfully",
        meta_data=rows
    )


@router.get("/my-modules", response_model=ApiResponse[list[dict]])
async def get_my_modules_lecturer_only(
    session: AsyncSessionDep,
    user: LecturerOnly,
):
    rows = await module_registration_service.get_lecturer_modules_with_student_count(
        session,
        user.iam_id,
    )
    return ApiResponse(
        message="My modules retrieved successfully",
        meta_data=rows,
    )


@router.get("/my-registrations", response_model=ApiResponse[List[ModuleRegistrationResponse]])
async def get_my_registrations_student_only(
    session: AsyncSessionDep,
    user: StudentOnly,
):
    records = await module_registration_service.find_registrations_by_student_id(
        session,
        user.iam_id,
    )
    return ApiResponse(message="My registrations retrieved successfully", meta_data=records)


@router.get("/all-modules-with-attendance", response_model=ApiResponse[list[dict]])
async def get_all_modules_with_attendance(
        session: AsyncSessionDep,
        _: AdminOrFA = None
):
    rows = await module_registration_service.get_all_modules_with_student_count_and_attendance_rate(session)
    return ApiResponse(
        message="All modules retrieved successfully",
        meta_data=rows
    )


@router.get(
    "/my-modules/students-attendance",
    response_model=ApiResponse[LecturerStudentsAttendanceResponse],
)
async def get_my_modules_students_attendance_lecturer_only(
    session: AsyncSessionDep,
    user: LecturerOnly,
    module_id: str | None = None,
):
    data = await module_registration_service.get_lecturer_students_with_attendance_rate(
        session=session,
        lecturer_id=user.iam_id,
        module_id=module_id,
    )
    return ApiResponse(
        message="My modules' students with attendance rates retrieved successfully",
        meta_data=data,
    )


@router.get("/{module_reg_id}", response_model=ApiResponse[ModuleRegistrationResponse])
async def get_module_registration_by_id(
        session: AsyncSessionDep,
        module_reg_id: int,
        _: AdminOrFAOrLecturer = None
):
    record = await module_registration_service.find_registration_by_id(session, module_reg_id)
    return ApiResponse(
        message="Module registration retrieved successfully",
        meta_data=record
    )



@router.put("/{module_reg_id}", response_model=ApiResponse[ModuleRegistrationResponse])
async def update_module_registration(session: AsyncSessionDep, module_reg_id: int, data: ModuleRegistrationUpdate, _: AdminOrFA = None):
    record = await module_registration_service.update_registration(session, module_reg_id, data)
    return ApiResponse(
        message="Module registration updated successfully",
        meta_data=record
    )


@router.delete("/{module_reg_id}", response_model=ApiResponse[None])
async def delete_module_registration(
        session: AsyncSessionDep,
        module_reg_id: int,
        _: AdminOrFA = None):
    await module_registration_service.delete_registration(session, module_reg_id)
    return ApiResponse(
        message="Module registration deleted successfully",
        meta_data=None
    )