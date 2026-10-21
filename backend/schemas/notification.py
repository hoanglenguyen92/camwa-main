from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.models.enums import NotificationType, NotificationStatus


class NotificationResponse(BaseModel):
    notification_id: int
    sender_id: str
    receiver_id: str
    notification_type: NotificationType
    request_id: int
    status: NotificationStatus
    created_at: datetime
    read_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class NotificationRequestCreate(BaseModel):
    sender_id: str
    receiver_id: str
    notification_type: NotificationType
    request_id: int
    status: NotificationStatus = NotificationStatus.UNREAD


class MarkAllAsRead(BaseModel):
    count: int