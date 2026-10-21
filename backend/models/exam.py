from datetime import datetime

from sqlalchemy import Integer, String, ForeignKey, Numeric, Boolean, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Exam(Base):
    __tablename__ = "exam"

    exam_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("module.module_id"), nullable=False)
    student_id: Mapped[str] = mapped_column(String(20), ForeignKey("student.student_id"), nullable=False)
    attendance_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    is_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    module: Mapped["Module"] = relationship(back_populates="exams")
    student: Mapped["Student"] = relationship(back_populates="exams")

    __table_args__ = (
        Index("ix_exam_student_id", "student_id"),
        Index("ix_exam_module_id", "module_id"),
    )
