from typing import Optional, List

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Student(Base):
    __tablename__ = "student"

    student_id: Mapped[str] = mapped_column(String(20), ForeignKey("iam.username"), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(40))
    map_location: Mapped[Optional[str]] = mapped_column(String(20))
    program_id: Mapped[Optional[str]] = mapped_column(String(20), ForeignKey("program.program_id"))
    intake: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("intake.year"))

    iam: Mapped["Iam"] = relationship(back_populates="student")
    program: Mapped[Optional["Program"]] = relationship(back_populates="students")
    intake_rel: Mapped[Optional["Intake"]] = relationship(back_populates="students")
    attendances: Mapped[List["Attendance"]] = relationship(back_populates="student")
    attendance_requests: Mapped[List["AttendanceRequest"]] = relationship(back_populates="student")
    exams: Mapped[List["Exam"]] = relationship(back_populates="student")
    module_registrations: Mapped[List["ModuleRegistration"]] = relationship(back_populates="student")
