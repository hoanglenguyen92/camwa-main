from typing import List

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Intake(Base):
    __tablename__ = "intake"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)

    students: Mapped[List["Student"]] = relationship(back_populates="intake_rel")
