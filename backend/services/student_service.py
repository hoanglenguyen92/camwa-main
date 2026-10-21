import io
from pathlib import Path
from typing import List, Optional

import openpyxl
from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Student, ModuleRegistration, Attendance, Exam, Iam, Program, Intake, Module, ImageAsset
from backend.models.enums import AttendanceStatus
from backend.schemas.student import StudentCreate, StudentResponse, StudentUpdate

PRESENT_STATUSES = [
    AttendanceStatus.PRESENT,
    AttendanceStatus.LATE,
    AttendanceStatus.EXCUSED,
]
async def _ensure_student_refs_exist(
    session: AsyncSession,
    student_id: Optional[str] = None,
    program_id: Optional[str] = None,
    intake: Optional[int] = None,
) -> None:
    if student_id and not await session.get(Iam, student_id):
        raise HTTPException(status_code=404, detail="IAM user not found for student")

    if program_id and not await session.get(Program, program_id):
        raise HTTPException(status_code=404, detail="Program not found")

    if intake is not None and not await session.get(Intake, intake):
        raise HTTPException(status_code=404, detail="Intake not found")


async def create_student(session: AsyncSession, data: StudentCreate) -> StudentResponse:
    existing = await session.get(Student, data.student_id)
    if existing:
        raise HTTPException(status_code=409, detail="Student already exists")
    await _ensure_student_refs_exist(
        session,
        student_id=data.student_id,
        program_id=data.program_id,
        intake=data.intake,
    )
    student = Student(**data.model_dump())
    session.add(student)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Could not create student")
    await session.refresh(student)
    return StudentResponse.model_validate(student)


async def get_all_students(session: AsyncSession) -> List[StudentResponse]:
    result = await session.execute(select(Student))
    students = result.scalars().all()
    return [StudentResponse.model_validate(student) for student in students]


async def find_student_by_id(session: AsyncSession, student_id: str) -> StudentResponse:
    student = await session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return StudentResponse.model_validate(student)


async def delete_student(session: AsyncSession, student_id: str) -> None:
    student = await session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    try:
        await session.delete(student)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete student because it is used by other records",
        )


async def update_student(
    session: AsyncSession,
    student_id: str,
    data: StudentUpdate,
) -> StudentResponse:
    student = await session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return StudentResponse.model_validate(student)
    await _ensure_student_refs_exist(
        session,
        program_id=update_data.get("program_id"),
        intake=update_data.get("intake"),
    )
    for field, value in update_data.items():
        setattr(student, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Could not update student")
    await session.refresh(student)
    return StudentResponse.model_validate(student)


async def get_student_modules_with_attendance_rate(session: AsyncSession, student_id: str):
    student = await session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    reg_result = await session.execute(
        select(ModuleRegistration).where(ModuleRegistration.student_id == student_id)
    )
    registrations = reg_result.scalars().all()
    payload = []
    for registration in registrations:
        module = await session.get(Module, registration.module_id)
        total_result = await session.execute(
            select(func.count(Attendance.attendance_id)).where(
                Attendance.student_id == student_id,
                Attendance.module_id == registration.module_id,
            )
        )
        total = total_result.scalar() or 0
        attended_result = await session.execute(
            select(func.count(Attendance.attendance_id)).where(
                Attendance.student_id == student_id,
                Attendance.module_id == registration.module_id,
                Attendance.attendance_status.in_(PRESENT_STATUSES),
            )
        )
        attended = attended_result.scalar() or 0
        payload.append({
            "module_reg_id": registration.module_reg_id,
            "module_id": registration.module_id,
            "module_name": module.name if module else "Unknown Module",
            "lecturer_id": module.lecturer_id if module else None,
            "program_id": module.program_id if module else None,
            "intake": module.intake if module else None,
            "semester_id": module.semester_id if module else None,
            "attendance_rate": round(attended / total * 100, 2) if total else 0.0,
            "total_classes": total,
            "attended_classes": attended,
            "registration_date": registration.created_at,
        })
    return payload


async def get_student_exam_eligibility_status(session: AsyncSession, student_id: str):
    student = await session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    result = await session.execute(
        select(Exam).where(Exam.student_id == student_id)
    )
    rows = result.scalars().all()
    if not rows:
        return {
            "message": "Currently there is no update about any exams for this student",
            "exam_records": [],
        }
    exam_records = []
    for row in rows:
        module = await session.get(Module, row.module_id)
        module_name = module.name if module else "Unknown Module"
        status_message = (
            f"This student is eligible for the exam in module {module_name}"
            if row.is_eligible
            else f"This student is not eligible for the exam in module {module_name}"
        )
        exam_records.append({
            "exam_id": row.exam_id,
            "module_id": row.module_id,
            "module_name": module_name,
            "lecturer_id": module.lecturer_id if module else None,
            "program_id": module.program_id if module else None,
            "intake": module.intake if module else None,
            "semester_id": module.semester_id if module else None,
            "attendance_rate": float(row.attendance_rate),
            "is_eligible": row.is_eligible,
            "eligibility_status": status_message,
            "exam_record_date": row.created_at,
        })
    return {
        "message": f"Found {len(exam_records)} exam record(s) for this student",
        "exam_records": exam_records,
    }


async def _process_excel(session: AsyncSession, file_contents: bytes):
    workbook = openpyxl.load_workbook(io.BytesIO(file_contents))
    sheet = workbook.active
    successful = []
    failed = []
    seen_student_ids = set()
    for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        student_id = str(row[0]).strip() if len(row) > 0 and row[0] else None
        intake_raw = str(row[2]).strip() if len(row) > 2 and row[2] else None
        program_id = str(row[3]).strip() if len(row) > 3 and row[3] else None
        name = str(row[4]).strip() if len(row) > 4 and row[4] else None
        map_location = str(row[5]).strip() if len(row) > 5 and row[5] else ""
        if not student_id or not name:
            failed.append({
                "row": row_index,
                "student_id": student_id,
                "name": name,
                "error": "Missing required fields",
            })
            continue
        try:
            intake = int(intake_raw) if intake_raw else None
        except ValueError:
            failed.append({
                "row": row_index,
                "student_id": student_id,
                "name": name,
                "error": f"Invalid intake value: {intake_raw}",
            })
            continue
        if student_id in seen_student_ids:
            failed.append({
                "row": row_index,
                "student_id": student_id,
                "name": name,
                "error": "Duplicate student in Excel file",
            })
            continue
        seen_student_ids.add(student_id)
        if await session.get(Student, student_id):
            failed.append({
                "row": row_index,
                "student_id": student_id,
                "name": name,
                "error": "Student already exists",
            })
            continue
        try:
            await _ensure_student_refs_exist(session, student_id, program_id, intake)
        except HTTPException as exc:
            failed.append({
                "row": row_index,
                "student_id": student_id,
                "name": name,
                "program_id": program_id,
                "intake": intake,
                "error": exc.detail,
            })
            continue
        student = Student(
            student_id=student_id,
            name=name,
            map_location=map_location,
            program_id=program_id,
            intake=intake,
        )
        session.add(student)
        successful.append({
            "student_id": student_id,
            "name": name,
            "map_location": map_location,
            "program_id": program_id,
            "intake": intake,
        })
    await session.commit()
    return {"successful": successful, "failed": failed}


async def create_multiple_student_from_excel(session: AsyncSession, file_contents: bytes):
    return await _process_excel(session, file_contents)


async def get_student_images(session: AsyncSession, student_id: str):
    student = await session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    result = await session.execute(
        select(ImageAsset).where(ImageAsset.username == student_id)
    )
    images = result.scalars().all()
    return {
        "message": f"Found {len(images)} image(s) for this student" if images else "No images found for this student",
        "student_id": student_id,
        "images": [
            {
                "image_id": image.image_id,
                "username": image.username,
                "image_path": image.image_path,
                "created_at": image.created_at,
                "updated_at": image.updated_at,
            }
            for image in images
        ],
    }


async def create_student_image(
    session: AsyncSession,
    student_id: str,
    image_path: Optional[str] = None,
):
    student = await session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    image = ImageAsset(
        username=student_id,
        image_path=image_path or f"image_assets/{student_id}.jpg",
    )
    session.add(image)
    await session.commit()
    await session.refresh(image)
    return {
        "message": "Image asset created successfully",
        "image": {
            "image_id": image.image_id,
            "username": image.username,
            "image_path": image.image_path,
            "created_at": image.created_at,
        },
    }


async def get_student_image_file(session: AsyncSession, student_id: str, image_id: int):
    result = await session.execute(
        select(ImageAsset).where(
            ImageAsset.username == student_id,
            ImageAsset.image_id == image_id,
        )
    )
    image = result.scalars().first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found for this student")
    return {
        "image_path": image.image_path,
        "username": image.username,
        "image_id": image.image_id,
    }

PROJECT_ROOT = Path(__file__).resolve().parents[2]

async def get_latest_student_image_path(session: AsyncSession, student_id: str) -> Path:
    student = await session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    result = await session.execute(
        select(ImageAsset)
        .where(ImageAsset.username == student_id)
        .order_by(ImageAsset.created_at.desc())
    )
    image = result.scalars().first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found for this student")
    raw_path = Path(image.image_path)
    file_path = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
    file_path = file_path.resolve()
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Image file not found on server")
    return file_path

