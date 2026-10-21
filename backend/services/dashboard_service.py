from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Student, Attendance
from backend.models.enums import AttendanceStatus
from backend.schemas.dashboard import DashboardStats


async def get_dashboard_stats(
        session: AsyncSession,
) -> DashboardStats:
    total_students_result = await session.execute(select(func.count(Student.student_id)))
    total_students = total_students_result.scalar() or 0
    present_students_result = await session.execute(
        select(func.count(Attendance.attendance_id)).where(Attendance.attendance_status == AttendanceStatus.PRESENT)
    )
    student_with_present_status = present_students_result.scalar() or 0
    return DashboardStats(
        total_students=total_students,
        students_with_present_status=student_with_present_status,
    )