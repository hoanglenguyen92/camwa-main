from fastapi import APIRouter, UploadFile, File, HTTPException, status

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOrFA, AllAuthenticated
from backend.helpers.response_wrapper import ApiResponse
from backend.schemas.lecturer import LecturerResponse, LecturerCreate, LecturerUpdate

from backend.services import lecturer_service

router = APIRouter(
    prefix="/lecturer",
    tags=["Lecturer"],
)


@router.post("/", response_model=ApiResponse[LecturerResponse], status_code=201)
async def create_lecturer(
        session: AsyncSessionDep,
        data: LecturerCreate,
        _: AdminOrFA = None
):
    lecturer = await lecturer_service.create_lecturer(session, data)
    return ApiResponse(
        message="Lecturer created successfully",
        meta_data=lecturer
    )


@router.post("/create-from-excel", response_model=ApiResponse)
async def import_lecturers(
    session: AsyncSessionDep,
    file: UploadFile = File(...),
    _: AdminOrFA = None,
):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only .xlsx files are allowed.",
        )
    contents = await file.read()
    result = await lecturer_service.create_multiple_lecturers_from_excel(session, contents)
    return ApiResponse(
        message="Lecturers imported successfully",
        meta_data={
            "successful": len(result.get("successful", [])),
            "failed": len(result.get("failed", [])),
            "details": result,
        },
    )


@router.get("/", response_model=ApiResponse[list[LecturerResponse]])
async def get_all_lecturers(session: AsyncSessionDep, _: AllAuthenticated = None):
    lecturers = await lecturer_service.get_all_lecturers(session)
    return ApiResponse(
        message="Lecturers retrieved successfully",
        meta_data=lecturers
    )


@router.get("/{lecturer_id}", response_model=ApiResponse[LecturerResponse])
async def get_lecturer_by_id(
        session: AsyncSessionDep,
        lecturer_id: str,
        _: AllAuthenticated = None,
):
    lecturer = await lecturer_service.find_lecturer_by_id(session, lecturer_id)
    return ApiResponse(
        message="Lecturer retrieved successfully",
        meta_data=lecturer
    )


@router.put("/{lecturer_id}", response_model=ApiResponse[LecturerResponse])
async def update_lecturer(
        session: AsyncSessionDep,
        lecturer_id: str,
        data: LecturerUpdate,
        _: AdminOrFA = None,
):
    lecturer = await lecturer_service.update_lecturer(session, lecturer_id, data)
    return ApiResponse(
        message="Lecturer updated successfully",
        meta_data=lecturer
    )


@router.delete("/{lecturer_id}", response_model=ApiResponse[None])
async def delete_lecturer(
        session: AsyncSessionDep,
        lecturer_id: str,
        _: AdminOrFA = None,
):
    await lecturer_service.delete_lecturer(session, lecturer_id)
    return ApiResponse(
        message="Lecturer deleted successfully",
        meta_data=None
    )


