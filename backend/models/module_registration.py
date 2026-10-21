from datetime import datetime

from sqlalchemy import Integer, String, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class ModuleRegistration(Base):
    __tablename__ = "module_registration"

    module_reg_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(20), ForeignKey("student.student_id"), nullable=False)
    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("module.module_id"), nullable=False)
    lecturer_id: Mapped[str] = mapped_column(String(20), ForeignKey("lecturer.lecturer_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="module_registrations")
    module: Mapped["Module"] = relationship(back_populates="module_registrations")
    lecturer: Mapped["Lecturer"] = relationship(back_populates="module_registrations")

    __table_args__ = (
        Index("ix_module_registration_student_id", "student_id"),
        Index("ix_module_registration_module_id", "module_id"),
        Index("ix_module_registration_lecturer_id", "lecturer_id"),
    )
