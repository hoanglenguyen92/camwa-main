from datetime import datetime
from typing import Optional

from backend.models.enums import NotificationType, NotificationStatus
from sqlalchemy import Integer, String, ForeignKey, Enum, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class Notification(Base):
    __tablename__ = "notification"

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_id: Mapped[str] = mapped_column(String(100), nullable=False)
    receiver_id: Mapped[str] = mapped_column(String(100), nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type_enum"), nullable=False
    )
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("attendance_request.request_id"), nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status_enum"), nullable=False, default=NotificationStatus.UNREAD
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    attendance_request: Mapped["AttendanceRequest"] = relationship(back_populates="notifications")

    __table_args__ = (
        Index("ix_notification_sender_id", "sender_id"),
        Index("ix_notification_receiver_id", "receiver_id"),
        Index("ix_notification_request_id", "request_id"),
        Index("ix_notification_status", "status"),
        Index("ix_notification_type", "notification_type"),
    )
