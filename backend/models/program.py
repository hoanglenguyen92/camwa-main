from typing import Optional, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Program(Base):
    __tablename__ = "program"

    program_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(50))

    students: Mapped[List["Student"]] = relationship(back_populates="program")
    modules: Mapped[List["Module"]] = relationship(back_populates="program")
    lecturers: Mapped[List["Lecturer"]] = relationship(back_populates="program")
    facility_faculties: Mapped[List["FacilityFaculty"]] = relationship(back_populates="program")
    academic_coordinators: Mapped[List["AcademicCoordinator"]] = relationship(back_populates="program")
