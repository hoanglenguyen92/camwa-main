from typing import Optional, List

from backend.models.enums import AccountRole
from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Iam(Base):
    __tablename__ = 'iam'

    iam_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    username: Mapped[str] = mapped_column(String(45), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    auth_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    role: Mapped[AccountRole] = mapped_column(String(45), nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    image_assets: Mapped[List["ImageAsset"]] = relationship(back_populates='iam')
    student: Mapped["Student"] = relationship(back_populates="iam")
