from datetime import datetime

from sqlalchemy import Integer, String, ForeignKey, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class ImageAsset(Base):
    __tablename__ = "image_assets"

    image_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(45), ForeignKey("iam.username"), nullable=False)
    image_path: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    iam: Mapped["Iam"] = relationship(back_populates="image_assets")
