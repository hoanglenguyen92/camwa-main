from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession


from backend.core.policies import FACULTY_INBOX
from backend.helpers.pagination import Page, PageParams, paginate
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
        receiver_id=FACULTY_INBOX,
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


async def list_notifications(
    session: AsyncSession, page: PageParams, scope: ColumnElement[bool], status: NotificationStatus | None = None
) -> Page[NotificationResponse]:
    stmt = select(Notification).where(scope).order_by(Notification.created_at.desc())
    if status:
        stmt = stmt.where(Notification.status == status)
    return await paginate(session, stmt, NotificationResponse, page)


async def count_unread(session: AsyncSession, scope: ColumnElement[bool]) -> int:
    count = await session.scalar(
        select(func.count()).select_from(Notification).where(scope, Notification.status == NotificationStatus.UNREAD)
    )
    return count or 0


async def find_notification(session: AsyncSession, notification_id: int, scope: ColumnElement[bool]) -> Notification:
    row = await session.scalar(
        select(Notification).where(Notification.notification_id == notification_id, scope)
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return row


def _set_status(row: Notification, new_status: NotificationStatus, now: datetime) -> None:
    row.status = new_status
    row.read_at = now if new_status == NotificationStatus.READ else None


async def update_notification_status(
    session: AsyncSession, row: Notification, new_status: NotificationStatus
) -> NotificationResponse:
    if row.status != new_status:
        _set_status(row, new_status, datetime.now())
        await session.commit()
        await session.refresh(row)
    return NotificationResponse.model_validate(row)


async def update_all_status(session: AsyncSession, scope: ColumnElement[bool], new_status: NotificationStatus) -> int:
    rows = (await session.scalars(select(Notification).where(scope, Notification.status != new_status))).all()
    now = datetime.now()
    for row in rows:
        _set_status(row, new_status, now)
    await session.commit()
    return len(rows)


async def delete_notification(session: AsyncSession, row: Notification) -> None:
    await session.delete(row)
    await session.commit()
