from fastapi import APIRouter

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOnly, AdminOrFA
from backend.helpers.response_wrapper import ApiResponse
from backend.schemas.program import ProgramResponse, ProgramCreate, ProgramUpdate
from backend.services import program_service

router = APIRouter(
    prefix="/program",
    tags=["Program"],
)


@router.post("/", response_model=ApiResponse[ProgramResponse], status_code=201)
async def create_program(
        session: AsyncSessionDep,
        data: ProgramCreate,
        _: AdminOnly = None
):
    program = await program_service.create_program(session, data)
    return ApiResponse(
        message="Program created successfully",
        meta_data=program
    )


@router.post("/{program_id}/students/{student_id}", response_model=ApiResponse[dict])
async def assign_student_to_program(
    session: AsyncSessionDep,
    program_id: str,
    student_id: str,
    _: AdminOrFA = None
):
    result = await program_service.assign_student_to_program(session, program_id, student_id)
    return ApiResponse(
        message=result["message"],
        meta_data=result
    )


@router.post("/{program_id}/lecturers/{lecturer_id}", response_model=ApiResponse[dict])
async def assign_lecturer_to_program(
    session: AsyncSessionDep,
    program_id: str,
    lecturer_id: str,
    _: AdminOrFA = None
):
    result = await program_service.assign_lecturer_to_program(session, program_id, lecturer_id)
    return ApiResponse(
        message=result["message"],
        meta_data=result
    )


@router.post("/{program_id}/modules/{module_id}", response_model=ApiResponse[dict])
async def assign_module_to_program(
    session: AsyncSessionDep,
    program_id: str,
    module_id: str,
    _: AdminOrFA = None
):
    result = await program_service.assign_module_to_program(session, program_id, module_id)
    return ApiResponse(
        message=result["message"],
        meta_data=result
    )


@router.get("/", response_model=ApiResponse[list[ProgramResponse]])
async def get_all_programs(
        session: AsyncSessionDep,
        _: AdminOrFA = None
):
    programs = await program_service.get_all_programs(session)
    return ApiResponse(
        message="Programs retrieved successfully",
        meta_data=programs
    )


@router.get("/{program_id}", response_model=ApiResponse[ProgramResponse])
async def find_program_by_id(
        session: AsyncSessionDep,
        program_id: str,
        _: AdminOrFA = None
):
    program = await program_service.find_program_by_id(session, program_id)
    return ApiResponse(
        message="Program retrieved successfully",
        meta_data=program
    )


@router.get("/{program_id}/modules", response_model=ApiResponse)
async def view_modules_in_program(
        session: AsyncSessionDep,
        program_id: str,
        _: AdminOrFA = None
):
    modules = await program_service.view_modules_in_program(session, program_id)
    return ApiResponse(
        message="Modules retrieved successfully",
        meta_data=modules
    )


@router.get("/{program_id}/lecturers", response_model=ApiResponse)
async def view_lecturers_in_program(
        session: AsyncSessionDep,
        program_id: str,
        _: AdminOrFA = None
):
    lecturers = await program_service.view_lecturers_in_program(session, program_id)
    return ApiResponse(
        message="Lecturers retrieved successfully",
        meta_data=lecturers
    )


@router.get("/{program_id}/students", response_model=ApiResponse)
async def view_students_in_program(
        session: AsyncSessionDep,
        program_id: str,
        _: AdminOrFA = None
):
    students = await program_service.view_students_in_program(session, program_id)
    return ApiResponse(
        message="Students retrieved successfully",
        meta_data=students
    )


@router.put("/{program_id}", response_model=ApiResponse[ProgramResponse])
async def update_program(
        session: AsyncSessionDep,
        program_id: str,
        data: ProgramUpdate,
        _: AdminOnly = None
):
    program = await program_service.update_program(session, program_id, data)
    return ApiResponse(
        message="Program updated successfully",
        meta_data=program
    )


@router.delete("/{program_id}", response_model=ApiResponse[None])
async def delete_program(
        session: AsyncSessionDep,
        program_id: str,
        _: AdminOnly = None
):
    await program_service.delete_program(session, program_id)
    return ApiResponse(
        message="Program deleted successfully",
        meta_data=None
    )