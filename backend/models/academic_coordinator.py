from sqlalchemy import String, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base
from backend.models.enums import CoordinatorRole


class AcademicCoordinator(Base):
    __tablename__ = "academic_coordinator"

    ac_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    program_id: Mapped[str] = mapped_column(String(20), ForeignKey("program.program_id"), nullable=False)
    current_role: Mapped[CoordinatorRole] = mapped_column(
        Enum(CoordinatorRole, name="coordinator_role_enum"), nullable=False
    )

    # Relationships
    program: Mapped["Program"] = relationship(back_populates="academic_coordinators")
