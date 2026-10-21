from datetime import date
from typing import Optional, List

from sqlalchemy import String, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Semester(Base):
    __tablename__ = "semester"

    sem_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)

    modules: Mapped[List["Module"]] = relationship(back_populates="semester")
