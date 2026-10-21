from datetime import datetime
from typing import Optional, List

from backend.models.enums import AccountRole
from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Iam(Base):
    __tablename__ = 'iam'

    iam_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    username: Mapped[str] = mapped_column(String(45), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[AccountRole] = mapped_column(String(45), nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    image_assets: Mapped[List["ImageAsset"]] = relationship(back_populates='iam')
    student: Mapped["Student"] = relationship(back_populates="iam")
