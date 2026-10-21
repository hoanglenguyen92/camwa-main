from datetime import datetime
from typing import Optional, List

from backend.models.enums import RequestStatus, AttendanceStatus
from sqlalchemy import Integer, String, ForeignKey, Enum, Text, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class AttendanceRequest(Base):
    __tablename__ = "attendance_request"

    request_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attendance_id: Mapped[int] = mapped_column(Integer, ForeignKey("attendance.attendance_id"), nullable=False)
    student_id: Mapped[str] = mapped_column(String(20), ForeignKey("student.student_id"), nullable=False)
    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("module.module_id"), nullable=False)
    request_status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, name="request_status_enum"), nullable=False, default=RequestStatus.PENDING
    )
    proposed_status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="proposed_status_enum"), nullable=False
    )
    approved_status: Mapped[Optional[AttendanceStatus]] = mapped_column(
        Enum(AttendanceStatus, name="approved_status_enum"), nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    attendance: Mapped["Attendance"] = relationship(back_populates="attendance_requests")
    student: Mapped["Student"] = relationship(back_populates="attendance_requests")
    notifications: Mapped[List["Notification"]] = relationship(back_populates="attendance_request")

    __table_args__ = (
        Index("ix_attendance_request_attendance_id", "attendance_id"),
        Index("ix_attendance_request_student_id", "student_id"),
        Index("ix_attendance_request_module_id", "module_id"),
        Index("ix_attendance_request_status", "request_status"),
        Index("ix_attendance_request_composite", "attendance_id", "student_id", "request_status"),
    )
