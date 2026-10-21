from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from backend.models import Notification, AttendanceRequest
from backend.models.enums import NotificationType, NotificationStatus
from backend.schemas.notification import NotificationRequestCreate, NotificationResponse


async def create_notification(session: AsyncSession, data: NotificationRequestCreate) -> NotificationResponse:
    notification = Notification(
        sender_id=data.sender_id,
        receiver_id=data.receiver_id,
        notification_type=data.notification_type,
        request_id=data.request_id,
        status=data.status,
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return NotificationResponse.model_validate(notification)


async def create_new_request_notification(session: AsyncSession, request_id: int, student_id: str) -> NotificationResponse:
    notification = NotificationRequestCreate(
        sender_id=student_id,
        receiver_id="FACULTY",
        notification_type=NotificationType.NEW_REQUEST,
        request_id=request_id,
        status=NotificationStatus.UNREAD,
    )
    return await create_notification(session, notification)


async def create_request_processed_notification(
        session: AsyncSession, request_id: int, processed_by: str, is_approved: bool
) -> NotificationResponse:
    req = await session.get(AttendanceRequest, request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance request not found")

    notification_type = (
        NotificationType.REQUEST_APPROVED if is_approved else NotificationType.REQUEST_REJECTED
    )
    notification = NotificationRequestCreate(
        sender_id=processed_by,
        receiver_id=req.student_id,
        notification_type=notification_type,
        request_id=request_id,
        status=NotificationStatus.UNREAD,
    )
    return await create_notification(session, notification)


async def get_notification_by_user(session: AsyncSession, receiver_id: str, status: NotificationStatus | None = None) -> list[NotificationResponse]:
    stmt = select(Notification).where(Notification.receiver_id == receiver_id).order_by(Notification.created_at.desc())
    if status:
        stmt = stmt.where(Notification.status == status)
    result = await session.execute(stmt)
    notifications = result.scalars().all()
    return [NotificationResponse.model_validate(notification) for notification in notifications]


async def mark_notification_as_read(
    session: AsyncSession,
    notification_id: int,
    receiver_id: str,
) -> NotificationResponse:
    row = await session.get(Notification, notification_id)
    if not row or row.receiver_id != receiver_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    if row.status != NotificationStatus.READ:
        row.status = NotificationStatus.READ
        row.read_at = datetime.now()
        await session.commit()
        await session.refresh(row)
    return NotificationResponse.model_validate(row)


async def mark_all_notifications_as_read(
    session: AsyncSession,
    receiver_id: str,
) -> dict:
    result = await session.execute(
        select(Notification).where(
            Notification.receiver_id == receiver_id,
            Notification.status == NotificationStatus.UNREAD,
        )
    )
    rows = result.scalars().all()
    now = datetime.now()
    for row in rows:
        row.status = NotificationStatus.READ
        row.read_at = now
    await session.commit()
    return {"count": len(rows)}


async def get_unread_notifications_count(
    session: AsyncSession,
    receiver_id: str,
) -> dict:
    result = await session.execute(
        select(Notification.notification_id).where(
            Notification.receiver_id == receiver_id,
            Notification.status == NotificationStatus.UNREAD,
        )
    )
    return {"count": len(result.scalars().all())}


async def delete_notification(session: AsyncSession, notification_id: int, receiver_id: str):
    row = await session.get(Notification, notification_id)
    if not row or row.receiver_id != receiver_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await session.delete(row)
    await session.commit()



