from datetime import datetime
from typing import List

from sqlalchemy import Integer, String, ForeignKey, Enum, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base
from backend.models.enums import AttendanceStatus


class Attendance(Base):
    __tablename__ = "attendance"

    attendance_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(20), ForeignKey("student.student_id"), nullable=False)
    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("module.module_id"), nullable=False)
    attendance_status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status_enum"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="attendances")
    module: Mapped["Module"] = relationship(back_populates="attendances")
    attendance_requests: Mapped[List["AttendanceRequest"]] = relationship(back_populates="attendance")

    __table_args__ = (
        Index("ix_attendance_student_id", "student_id"),
        Index("ix_attendance_module_id", "module_id"),
        Index("ix_attendance_student_module", "student_id", "module_id"),
    )
