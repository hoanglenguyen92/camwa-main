from fastapi import APIRouter, UploadFile, File, HTTPException, status
from starlette.responses import FileResponse

from backend.core.db import AsyncSessionDep
from backend.core.deps import CurrentUser, AdminOrFA, StudentOnly, AllAuthenticated
from backend.helpers.response_wrapper import ApiResponse
from backend.schemas.student import StudentResponse, StudentCreate, StudentUpdate, StudentImageCreate
from backend.services import student_service

router = APIRouter(
    prefix="/student",
    tags=["Student"],
)

def _ensure_student_self_access(user, student_id: str) -> None:
    if user.role == "STUDENT" and user.iam_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students can only access their own data",
        )



@router.post("/create", response_model=ApiResponse[StudentResponse], status_code=201)
async def create_student(
        session: AsyncSessionDep,
        data: StudentCreate,
        _: AdminOrFA = None,
):
    student = await student_service.create_student(session, data)
    return ApiResponse(
        message="Student created successfully",
        meta_data=student
    )


@router.post("/{student_id}/images", response_model=ApiResponse)
async def create_student_image(
    session: AsyncSessionDep,
    student_id: str,
    data: StudentImageCreate,
    _: AdminOrFA = None,
):
    result = await student_service.create_student_image(session, student_id, data.image_path)
    return ApiResponse(
        message="Student image created successfully",
        meta_data=result
    )


@router.post("/create-from-excel", response_model=ApiResponse)
async def import_students(
        session: AsyncSessionDep,
        file: UploadFile = File(...),
        _: AdminOrFA = None,
):
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in [".xlsx", ".xls"]):
        raise HTTPException(status_code=400, detail="Invalid file type. Only Excel files are allowed.")

    contents = await file.read()
    result = await student_service.create_multiple_student_from_excel(session, contents)
    return ApiResponse(
        message="Students imported successfully",
        meta_data=result
    )


@router.get("/all", response_model=ApiResponse[list[StudentResponse]])
async def get_all_students(session: AsyncSessionDep):
    students = await student_service.get_all_students(session)
    return ApiResponse(
        message="Students retrieved successfully",
        meta_data=students
    )


@router.get("/{student_id}", response_model=ApiResponse[StudentResponse])
async def get_student_by_id(session: AsyncSessionDep, student_id: str):
    student = await student_service.find_student_by_id(session, student_id)
    return ApiResponse(
        message="Student retrieved successfully",
        meta_data=student
    )



@router.get("/my/modules-with-attendance", response_model=ApiResponse)
async def get_my_modules_with_attendance(
    session: AsyncSessionDep,
    user: StudentOnly,
):
    result = await student_service.get_student_modules_with_attendance_rate(
        session,
        user.iam_id,
    )
    return ApiResponse(
        message="My modules with attendance rates retrieved successfully",
        meta_data=result,
    )


@router.get("/my/exam-eligibility-status", response_model=ApiResponse)
async def get_my_exam_eligibility(
    session: AsyncSessionDep,
    user: StudentOnly,
):
    result = await student_service.get_student_exam_eligibility_status(
        session,
        user.iam_id,
    )
    return ApiResponse(
        message="My exam eligibility status retrieved successfully",
        meta_data=result,
    )


@router.get("/my/images")
async def get_my_images(
    session: AsyncSessionDep,
    user: StudentOnly,
):
    file_path = await student_service.get_latest_student_image_path(session, user.iam_id)
    return FileResponse(file_path)


@router.get("/{student_id}/modules-with-attendance", response_model=ApiResponse)
async def get_student_modules_with_attendance(
    session: AsyncSessionDep,
    student_id: str,
    _: AdminOrFA = None,
):

    result = await student_service.get_student_modules_with_attendance_rate(session, student_id)
    return ApiResponse(
        message="Student modules with attendance rates retrieved successfully",
        meta_data=result
    )


@router.get("/{student_id}/exam-eligibility-status", response_model=ApiResponse)
async def get_student_exam_eligibility(
    session: AsyncSessionDep,
    student_id: str,
    user: AllAuthenticated,
):
    _ensure_student_self_access(user, student_id)

    result = await student_service.get_student_exam_eligibility_status(session, student_id)
    return ApiResponse(
        message="Student exam eligibility status retrieved successfully",
        meta_data=result
    )


@router.get("/{student_id}/images/{image_id}/info", response_model=ApiResponse)
async def get_student_image_info(
    session: AsyncSessionDep,
    student_id: str,
    image_id: int,
    user: AllAuthenticated,
):
    _ensure_student_self_access(user, student_id)

    result = await student_service.get_student_image_file(session, student_id, image_id)
    return ApiResponse(
        message="Student image file info retrieved successfully",
        meta_data=result
    )


@router.put("/{student_id}", response_model=ApiResponse[StudentResponse])
async def update_student(
        session: AsyncSessionDep,
        student_id: str,
        data: StudentUpdate,
        _: AdminOrFA = None,
):
    student = await student_service.update_student(session, student_id, data)
    return ApiResponse(
        message="Student updated successfully",
        meta_data=student
    )


@router.delete("/{student_id}", response_model=ApiResponse[None])
async def delete_student(
        session: AsyncSessionDep,
        student_id: str,
        _: AdminOrFA = None,
):
    await student_service.delete_student(session, student_id)
    return ApiResponse(
        message="Student deleted successfully",
        meta_data=None
    )




