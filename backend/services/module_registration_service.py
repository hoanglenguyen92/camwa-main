import io
from collections import defaultdict
from typing import List, Optional, Dict, Any

import openpyxl
from fastapi import HTTPException, status
from sqlalchemy import select, func, case, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import ModuleRegistration, Attendance, Student, Module, Lecturer
from backend.models.enums import AttendanceStatus
from backend.schemas.module_registration import ModuleRegistrationCreate, ModuleRegistrationResponse, \
    ModuleRegistrationUpdate


PRESENT_STATUSES = [
    AttendanceStatus.PRESENT,
    AttendanceStatus.LATE,
    AttendanceStatus.EXCUSED,
]


async def _ensure_refs_exist(
    session: AsyncSession,
    student_id: Optional[str] = None,
    module_id: Optional[str] = None,
    lecturer_id: Optional[str] = None,
) -> None:
    if student_id and not await session.get(Student, student_id):
        raise HTTPException(status_code=404, detail="Student not found")

    if module_id and not await session.get(Module, module_id):
        raise HTTPException(status_code=404, detail="Module not found")

    if lecturer_id and not await session.get(Lecturer, lecturer_id):
        raise HTTPException(status_code=404, detail="Lecturer not found")


async def _registration_exists(
    session: AsyncSession,
    student_id: str,
    module_id: str,
    exclude_id: Optional[int] = None,
) -> bool:
    stmt = select(ModuleRegistration).where(
        ModuleRegistration.student_id == student_id,
        ModuleRegistration.module_id == module_id,
    )
    if exclude_id:
        stmt = stmt.where(ModuleRegistration.module_reg_id != exclude_id)
    result = await session.execute(stmt)
    return result.scalars().first() is not None


async def create_registration(
    session: AsyncSession,
    data: ModuleRegistrationCreate,
) -> ModuleRegistrationResponse:
    await _ensure_refs_exist(
        session,
        student_id=data.student_id,
        module_id=data.module_id,
        lecturer_id=data.lecturer_id,
    )
    if await _registration_exists(session, data.student_id, data.module_id):
        raise HTTPException(status_code=409, detail="Registration already exists")
    registration = ModuleRegistration(**data.model_dump())
    session.add(registration)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Could not create registration")
    await session.refresh(registration)
    return ModuleRegistrationResponse.model_validate(registration)


async def get_all_registrations(session: AsyncSession) -> List[ModuleRegistrationResponse]:
    result = await session.execute(select(ModuleRegistration))
    rows = result.scalars().all()
    return [ModuleRegistrationResponse.model_validate(row) for row in rows]


async def find_registration_by_id(session: AsyncSession, module_reg_id: int) -> ModuleRegistrationResponse:
    row = await session.get(ModuleRegistration, module_reg_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")
    return ModuleRegistrationResponse.model_validate(row)


async def find_registrations_by_student_id(session: AsyncSession, student_id: str) -> List[ModuleRegistrationResponse]:
    result = await session.execute(select(ModuleRegistration).where(ModuleRegistration.student_id == student_id))
    rows = result.scalars().all()
    return [ModuleRegistrationResponse.model_validate(row) for row in rows]


async def find_registrations_by_module_id(session: AsyncSession, module_id: str) -> List[ModuleRegistrationResponse]:
    result = await session.execute(select(ModuleRegistration).where(ModuleRegistration.module_id == module_id))
    rows = result.scalars().all()
    return [ModuleRegistrationResponse.model_validate(row) for row in rows]


async def get_lecturer_modules_with_student_count(session: AsyncSession, lecturer_id: str) -> list[dict]:
    rows = (
        await session.execute(
            select(
                ModuleRegistration.module_id,
                func.count(ModuleRegistration.student_id).label("student_count"),
            )
            .where(ModuleRegistration.lecturer_id == lecturer_id)
            .group_by(ModuleRegistration.module_id)
        )
    ).all()
    payload = []
    for module_id, student_count in rows:
        att = (
            await session.execute(
                select(
                    func.count(Attendance.attendance_id),
                    func.sum(
                        case(
                            (Attendance.attendance_status.in_(PRESENT_STATUSES), 1),
                            else_=0,
                        )
                    ),
                ).where(Attendance.module_id == module_id)
            )
        ).first()
        total = att[0] or 0
        attended = att[1] or 0
        rate = round((attended / total * 100), 2) if total else 0.0
        payload.append({
            "module_id": module_id,
            "student_count": student_count,
            "attendance_rate": f"{rate:.2f}%",
            "total_attendance_records": total,
            "absent_count": total - attended,
        })
    return payload


async def get_all_modules_with_student_count_and_attendance_rate(session: AsyncSession) -> list[dict]:
    reg_result = await session.execute(
        select(ModuleRegistration.module_id, func.count(ModuleRegistration.student_id))
        .group_by(ModuleRegistration.module_id)
    )
    registrations = reg_result.all()
    att_result = await session.execute(
        select(
            Attendance.module_id,
            func.count(Attendance.attendance_id).label("total"),
            func.sum(case((Attendance.attendance_status.in_(PRESENT_STATUSES), 1), else_=0)).label("attended"),
        ).group_by(Attendance.module_id)
    )
    attendance = att_result.all()
    att_map = {module_id: (total or 0, present or 0) for module_id, total, present in attendance}
    payload = []
    for module_id, student_count in registrations:
        total, present = att_map.get(module_id, (0, 0))
        rate = (present / total * 100.0) if total else 0.0
        payload.append({"module_id": module_id, "student_count": student_count, "attendance_rate": round(rate, 2)})
    return payload


async def get_lecturer_students_with_attendance_rate(
    session,
    lecturer_id: str,
    module_id: Optional[str] = None,
) -> Dict[str, Any]:

    module_stmt = select(Module.module_id, Module.name).where(Module.lecturer_id == lecturer_id)
    if module_id:
        module_stmt = module_stmt.where(Module.module_id == module_id)
    module_rows = (await session.execute(module_stmt)).all()
    if not module_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No modules found for this lecturer",
        )
    module_map = {m_id: m_name for m_id, m_name in module_rows}
    module_ids = list(module_map.keys())

    reg_stmt = (
        select(
            ModuleRegistration.module_id,
            Student.student_id,
            Student.name,
        )
        .join(Student, Student.student_id == ModuleRegistration.student_id)
        .where(
            ModuleRegistration.lecturer_id == lecturer_id,
            ModuleRegistration.module_id.in_(module_ids),
        )
    )
    reg_rows = (await session.execute(reg_stmt)).all()

    if not reg_rows:
        return {
            "lecturer_id": lecturer_id,
            "modules": [
                {
                    "module_id": mid,
                    "module_name": module_map[mid],
                    "students": [],
                }
                for mid in module_ids
            ],
        }

    att_stmt = (
        select(
            Attendance.module_id,
            Attendance.student_id,
            func.count(Attendance.attendance_id).label("total_classes"),
            func.sum(
                case(
                    (Attendance.attendance_status.in_(PRESENT_STATUSES), 1),
                    else_=0,
                )
            ).label("attended_classes"),
        )
        .where(
            Attendance.module_id.in_(module_ids),
        )
        .group_by(Attendance.module_id, Attendance.student_id)
    )
    att_rows = (await session.execute(att_stmt)).all()
    attendance_map = {
        (m_id, s_id): (int(total or 0), int(attended or 0))
        for m_id, s_id, total, attended in att_rows
    }

    grouped = defaultdict(list)
    for m_id, s_id, s_name in reg_rows:
        total, attended = attendance_map.get((m_id, s_id), (0, 0))
        rate = round((attended / total) * 100, 2) if total else 0.0
        grouped[m_id].append(
            {
                "student_id": s_id,
                "student_name": s_name,
                "attendance_rate": rate,
                "total_classes": total,
                "attended_classes": attended,
            }
        )
    modules_payload = []
    for mid in module_ids:
        modules_payload.append(
            {
                "module_id": mid,
                "module_name": module_map[mid],
                "students": grouped.get(mid, []),
            }
        )
    return {
        "lecturer_id": lecturer_id,
        "modules": modules_payload,
    }



async def update_registration(
    session: AsyncSession,
    module_reg_id: int,
    data: ModuleRegistrationUpdate,
) -> ModuleRegistrationResponse:
    row = await session.get(ModuleRegistration, module_reg_id)
    if not row:
        raise HTTPException(status_code=404, detail="Registration not found")
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return ModuleRegistrationResponse.model_validate(row)
    await _ensure_refs_exist(
        session,
        student_id=update_data.get("student_id"),
        module_id=update_data.get("module_id"),
        lecturer_id=update_data.get("lecturer_id"),
    )
    next_student_id = update_data.get("student_id", row.student_id)
    next_module_id = update_data.get("module_id", row.module_id)
    if await _registration_exists(session, next_student_id, next_module_id, module_reg_id):
        raise HTTPException(status_code=409, detail="Registration already exists")
    for field, value in update_data.items():
        setattr(row, field, value)
    await session.commit()
    await session.refresh(row)
    return ModuleRegistrationResponse.model_validate(row)


async def delete_registration(session: AsyncSession, module_reg_id: int) -> None:
    row = await session.get(ModuleRegistration, module_reg_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")
    await session.delete(row)
    await session.commit()


async def _process_excel(session: AsyncSession, file_contents: bytes):
    workbook = openpyxl.load_workbook(io.BytesIO(file_contents))
    sheet = workbook.active
    successful = []
    failed = []
    seen_pairs = set()
    for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        student_id = str(row[0]).strip() if len(row) > 0 and row[0] else None
        module_id = str(row[5]).strip() if len(row) > 5 and row[5] else None
        lecturer_id = str(row[7]).strip() if len(row) > 7 and row[7] else None
        if not student_id or not module_id or not lecturer_id:
            failed.append({
                "row": row_index,
                "student_id": student_id,
                "module_id": module_id,
                "lecturer_id": lecturer_id,
                "error": "Missing required fields",
            })
            continue
        pair = (student_id, module_id)
        if pair in seen_pairs:
            failed.append({
                "row": row_index,
                "student_id": student_id,
                "module_id": module_id,
                "error": "Duplicate registration in Excel file",
            })
            continue
        seen_pairs.add(pair)
        try:
            await _ensure_refs_exist(session, student_id, module_id, lecturer_id)
        except HTTPException as exc:
            failed.append({
                "row": row_index,
                "student_id": student_id,
                "module_id": module_id,
                "lecturer_id": lecturer_id,
                "error": exc.detail,
            })
            continue
        if await _registration_exists(session, student_id, module_id):
            failed.append({
                "row": row_index,
                "student_id": student_id,
                "module_id": module_id,
                "error": "Registration already exists",
            })
            continue
        registration = ModuleRegistration(
            student_id=student_id,
            module_id=module_id,
            lecturer_id=lecturer_id,
        )
        session.add(registration)
        await session.flush()
        successful.append({
            "module_reg_id": registration.module_reg_id,
            "student_id": student_id,
            "module_id": module_id,
            "lecturer_id": lecturer_id,
        })
    await session.commit()
    return {"successful": successful, "failed": failed}


async def create_multiple_module_registration_from_excel(session: AsyncSession, file_contents: bytes):
    return await _process_excel(session, file_contents)

