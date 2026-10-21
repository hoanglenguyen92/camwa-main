from typing import Optional, List

from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Module(Base):
    __tablename__ = "module"

    module_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    lecturer_id: Mapped[str] = mapped_column(String(20), ForeignKey("lecturer.lecturer_id"), nullable=False)
    program_id: Mapped[str] = mapped_column(String(20), ForeignKey("program.program_id"), nullable=False)
    intake: Mapped[int] = mapped_column(Integer, ForeignKey("intake.year"), nullable=False)
    semester_id: Mapped[str] = mapped_column(String(36), ForeignKey("semester.sem_id"), nullable=False)
    camera_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Increased length

    lecturer: Mapped["Lecturer"] = relationship(back_populates="modules")
    program: Mapped["Program"] = relationship(back_populates="modules")
    semester: Mapped["Semester"] = relationship(back_populates="modules")
    attendances: Mapped[List["Attendance"]] = relationship(back_populates="module")
    exams: Mapped[List["Exam"]] = relationship(back_populates="module")
    module_registrations: Mapped[List["ModuleRegistration"]] = relationship(back_populates="module")
