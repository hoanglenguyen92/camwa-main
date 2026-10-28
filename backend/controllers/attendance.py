from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, UploadFile, File

from backend.core.db import AsyncSessionDep
from backend.helpers.response_wrapper import ApiResponse
from backend.models.enums import RequestStatus
from backend.schemas.attendance import AttendanceResponse, AttendanceCreate, AttendanceUpdate, \
    AttendanceRequestResponse, AttendanceRequestCreate, CorrectionApproval, ExamEligibilityResponse
from backend.services import attendance_service

from backend.core.deps import (
    AdminOnly,
    AdminOrFA,
    AdminOrFAOrAC,
    AdminOrFAOrLecturer,
    AllAuthenticated,
    LecturerOnly,
    StudentOnly,
)

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"],
)

ALLOWED_EXCEL_EXTENSIONS = (".xlsx", ".xls")


def _ensure_student_self_access(user, student_id: Optional[str]) -> None:
    if user.role == "STUDENT" and student_id and user.iam_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students can only access their own attendance data",
        )


def _ensure_lecturer_self_access(user, lecturer_id: str) -> None:
    if user.role == "LECTURER" and user.iam_id != lecturer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lecturers can only access their own modules",
        )


def _validate_excel_upload(file: UploadFile) -> None:
    name = (file.filename or "").lower()
    if not name.endswith(ALLOWED_EXCEL_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx and .xls files are allowed",
        )


def _strip_exam_records(module_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Remove non-serialisable ORM ``Exam`` instances from per-module summaries."""
    cleaned: Dict[str, Any] = {k: v for k, v in module_summary.items() if k != "results"}
    if "results" in module_summary:
        cleaned["results"] = [
            {k: v for k, v in entry.items() if k != "exam_record"}
            for entry in module_summary["results"]
        ]
    return cleaned


@router.post("/create", response_model=ApiResponse[AttendanceResponse], status_code=201)
async def submit_attendance(
        session: AsyncSessionDep,
        data: AttendanceCreate,
        user: AllAuthenticated,
):
    _ensure_student_self_access(user, data.student_id)

    attendance = await attendance_service.submit_attendance(session, data)
    return ApiResponse(
        message="Attendance submitted successfully",
        meta_data=attendance
    )


@router.post("/request-correction", response_model=ApiResponse[AttendanceRequestResponse], status_code=201)
async def request_correction(
        session: AsyncSessionDep,
        background_task: BackgroundTasks,
        data: AttendanceRequestCreate,
        user: StudentOnly,
):
    if user.iam_id != data.student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students can only request corrections for their own attendance",
        )

    result = await attendance_service.request_correction(session, background_task, data)
    return ApiResponse(
        message="Correction request submitted successfully",
        meta_data=result
    )


@router.post("/create-from-excel", response_model=ApiResponse[dict])
async def import_attendance_from_excel(
        session: AsyncSessionDep,
        file: UploadFile = File(...),
        _: AdminOrFA = None,
):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are allowed")

    file_bytes = await file.read()
    result = await attendance_service.import_attendance_from_excel(session, file_bytes)

    return ApiResponse(
        message="Attendance imported successfully",
        meta_data={
            "successful": len(result.get("successful", [])),
            "failed": len(result.get("failed", [])),
            "errors": result.get("errors", [])
        }
    )


@router.post(
    "/exam-eligibility/module/{module_id}",
    response_model=ApiResponse[List[Dict[str, Any]]],
)
async def update_exam_eligibility_for_module(
    session: AsyncSessionDep,
    module_id: str,
    _: AdminOrFA,
):
    results = await attendance_service.update_eligibility_for_module(
        session, module_id
    )
    return ApiResponse(
        message="Exam eligibility updated successfully",
        meta_data=[
            {k: v for k, v in entry.items() if k != "exam_record"}
            for entry in results
        ],
    )


@router.post(
    "/exam-eligibility/update-all-modules",
    response_model=ApiResponse[Dict[str, Any]],
)
async def update_exam_eligibility_for_all_modules(
    session: AsyncSessionDep,
    _: AdminOrFA,
):
    data = await attendance_service.update_exam_eligibility_for_all_modules(session)
    return ApiResponse(
        message="Exam eligibility updated for all modules",
        meta_data={
            "summary": data["summary"],
            "modules": [_strip_exam_records(m) for m in data["modules"]],
        },
    )


@router.post(
    "/exam-eligibility/lecturer/{lecturer_id}/update",
    response_model=ApiResponse[Dict[str, Any]],
)
async def update_exam_eligibility_for_lecturer(
    session: AsyncSessionDep,
    lecturer_id: str,
    user: LecturerOnly,
):
    _ensure_lecturer_self_access(user, lecturer_id)

    data = await attendance_service.update_exam_eligibility_for_lecturer_modules(
        session, lecturer_id
    )
    return ApiResponse(
        message="Exam eligibility updated for lecturer's modules",
        meta_data={
            "lecturer_id": data["lecturer_id"],
            "summary": data["summary"],
            "modules": [_strip_exam_records(m) for m in data["modules"]],
        },
    )


@router.post(
    "/exam-eligibility/lecturer/{lecturer_id}/export",
    response_model=ApiResponse[Dict[str, Any]],
)
async def export_exam_eligibility_for_lecturer(
    session: AsyncSessionDep,
    lecturer_id: str,
    user: LecturerOnly,
):
    _ensure_lecturer_self_access(user, lecturer_id)

    result = await attendance_service.export_exam_eligibility_for_lecturer_to_excel(
        session, lecturer_id
    )
    return ApiResponse(
        message="Exam eligibility exported for lecturer's modules",
        meta_data=result,
    )


@router.post(
    "/exam-eligibility/export",
    response_model=ApiResponse[Dict[str, Any]],
)
async def export_exam_eligibility(
    session: AsyncSessionDep,
    _: AdminOrFAOrAC,
):
    result = await attendance_service.export_exam_eligibility_to_excel(session)
    return ApiResponse(
        message="Exam eligibility exported successfully",
        meta_data=result,
    )



@router.get("/view", response_model=ApiResponse[List[AttendanceResponse]])
async def view_attendance(
    session: AsyncSessionDep,
    user: AllAuthenticated,
    student_id: Optional[str] = None,
    module_id: Optional[str] = None,
):
    if user.role == "STUDENT":
        student_id = user.iam_id
    if module_id and user.role != "STUDENT":
        result = await attendance_service.view_by_module(session, module_id)
    elif student_id:
        result = await attendance_service.view_by_student(session, student_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'student_id' or 'module_id' query parameter",
        )
    return ApiResponse(message="Attendance retrieved successfully", meta_data=result)


@router.get("/requests", response_model=ApiResponse[List[AttendanceRequestResponse]])
async def get_attendance_requests(
    session: AsyncSessionDep,
    _: AdminOrFAOrLecturer,
    request_status: Optional[RequestStatus] = None,
    module_id: Optional[str] = None,
):
    rows = await attendance_service.get_request_by_status(
        session, request_status, module_id
    )
    return ApiResponse(
        message="Attendance requests retrieved successfully",
        meta_data=rows,
    )


@router.get(
    "/requests/student/{student_id}",
    response_model=ApiResponse[List[AttendanceRequestResponse]],
)
async def get_requests_by_student(
        session: AsyncSessionDep,
        student_id: str
):
    rows = await attendance_service.view_attendance_requests_by_student(
        session, student_id
    )
    return ApiResponse(
        message="Attendance requests retrieved successfully",
        meta_data=rows,
    )


@router.get(
    "/requests/module/{module_id}",
    response_model=ApiResponse[List[AttendanceRequestResponse]],
)
async def get_requests_by_module(
        session: AsyncSessionDep,
        module_id: str
):
    rows = await attendance_service.view_attendance_requests_by_module(
        session, module_id
    )
    return ApiResponse(
        message="Attendance requests retrieved successfully",
        meta_data=rows,
    )


@router.get(
    "/exam-eligibility",
    response_model=ApiResponse[List[ExamEligibilityResponse]],
)
async def get_exam_eligibility(
    session: AsyncSessionDep,
    user: AllAuthenticated,
    student_id: Optional[str] = None,
    module_id: Optional[str] = None,
):
    if user.role == "STUDENT":
        student_id = user.iam_id

    if module_id:
        records = await attendance_service.get_exam_eligibility_by_module(
            session, module_id
        )
    elif student_id:
        records = await attendance_service.get_exam_eligibility_by_student(
            session, student_id
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'student_id' or 'module_id' query parameter",
        )
    return ApiResponse(
        message="Exam eligibility retrieved successfully",
        meta_data=records
    )


@router.get(
    "/exam-eligibility/check",
    response_model=ApiResponse[Dict[str, Any]],
)
async def check_exam_eligibility(
    session: AsyncSessionDep,
    user: AllAuthenticated,
    student_id: str,
    module_id: str
):
    _ensure_student_self_access(user, student_id)

    result = await attendance_service.check_exam_eligibility(
        session, student_id, module_id
    )
    exam_record = result.get("exam_record")
    if hasattr(exam_record, "exam_id"):
        result["exam_record"] = ExamEligibilityResponse.model_validate(
            exam_record
        ).model_dump()
    return ApiResponse(
        message="Exam eligibility checked successfully",
        meta_data=result,
    )


@router.put("/correction/{request_id}", response_model=ApiResponse[dict])
async def handle_correction(
        session: AsyncSessionDep,
        request_id: int,
        approval: CorrectionApproval,
        background_task: BackgroundTasks,
        _: AdminOrFA,
):
    result = await attendance_service.handle_correction(session, background_task, request_id, approval)
    return ApiResponse(
        message="Correction request handled successfully",
        meta_data=result
    )


@router.put("/{attendance_id}", response_model=ApiResponse[AttendanceResponse])
async def update_attendance(
        session: AsyncSessionDep,
        attendance_id: int,
        data: AttendanceUpdate,
        _: AdminOrFA
):
    result = await attendance_service.update_attendance(session, attendance_id, data)
    return ApiResponse(
        message="Attendance updated successfully",
        meta_data=result,
    )


@router.delete("/{attendance_id}", response_model=ApiResponse[None])
async def delete_attendance(
        session: AsyncSessionDep,
        attendance_id: int,
        _: AdminOrFA
):
    await attendance_service.delete_attendance(session, attendance_id)
    return ApiResponse(
        message="Attendance deleted successfully",
        meta_data=None
    )


@router.delete("/requests/{request_id}", response_model=ApiResponse[None])
async def delete_attendance_request(
        session: AsyncSessionDep,
        request_id: int
):
    await attendance_service.delete_attendance_request(session, request_id)
    return ApiResponse(
        message="Attendance request deleted successfully",
        meta_data=None,
    )





















