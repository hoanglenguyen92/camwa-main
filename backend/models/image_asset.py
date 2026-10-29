from datetime import datetime

from sqlalchemy import Integer, String, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class ImageAsset(Base):
    __tablename__ = "image_assets"

    image_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camwa_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    image_path: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
