from fastapi import APIRouter

from backend.core.db import AsyncSessionDep
from backend.core.deps import CurrentUser, AllAuthenticated
from backend.helpers.response_wrapper import ApiResponse
from backend.models.enums import NotificationStatus
from backend.schemas.notification import NotificationResponse
from backend.services import notification_service

router = APIRouter(
    prefix="/notification",
    tags=["Notification"],
)


@router.get("/", response_model=ApiResponse[list[NotificationResponse]])
async def get_all_notifications(
    session: AsyncSessionDep,
    user: AllAuthenticated,
    status: NotificationStatus | None = None,
):
    rows = await notification_service.get_notification_by_user(
        session,
        user.iam_id,
        status,
    )
    return ApiResponse(
        message="Notifications retrieved successfully",
        meta_data=rows,
    )


@router.get("/unread-count", response_model=ApiResponse)
async def get_unread_count(
        session: AsyncSessionDep,
        user: AllAuthenticated
):
    count = await notification_service.get_unread_notifications_count(
        session,
        user.iam_id,
    )
    return ApiResponse(
        message="Unread notifications count retrieved successfully",
        meta_data=count,
    )


@router.put("/{notification_id}/read", response_model=ApiResponse[NotificationResponse])
async def mark_notification_as_read(
    session: AsyncSessionDep,
    notification_id: int,
    user: AllAuthenticated,
):
    row = await notification_service.mark_notification_as_read(
        session,
        notification_id,
        user.iam_id,
    )
    return ApiResponse(
        message="Notification marked as read successfully",
        meta_data=row,
    )


@router.put("/mark-all-read", response_model=ApiResponse)
async def mark_all_notifications_as_read(
    session: AsyncSessionDep,
    user: AllAuthenticated,
):
    count = await notification_service.mark_all_notifications_as_read(
        session,
        user.iam_id,
    )
    return ApiResponse(
        message="All notifications marked as read successfully",
        meta_data=count,
    )

@router.delete("/{notification_id}", response_model=ApiResponse)
async def delete_notification(
    session: AsyncSessionDep,
    notification_id: int,
    user: AllAuthenticated,
):
    await notification_service.delete_notification(
        session,
        notification_id,
        user.iam_id,
    )
    return ApiResponse(
        message="Notification deleted successfully",
        meta_data=None,
    )