from typing import List

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Lecturer(Base):
    __tablename__ = "lecturer"

    lecturer_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    program_id: Mapped[str] = mapped_column(String(20), ForeignKey("program.program_id"), nullable=False)

    program: Mapped["Program"] = relationship(back_populates="lecturers")
    modules: Mapped[List["Module"]] = relationship(back_populates="lecturer")
    module_registrations: Mapped[List["ModuleRegistration"]] = relationship(back_populates="lecturer")
