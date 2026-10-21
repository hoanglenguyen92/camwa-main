from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class FacilityFaculty(Base):
    __tablename__ = "facility_faculty"

    staff_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    program_id: Mapped[str] = mapped_column(String(20), ForeignKey("program.program_id"), nullable=False)

    # Relationships
    program: Mapped["Program"] = relationship(back_populates="facility_faculties")
