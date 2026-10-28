from fastapi import APIRouter

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOnly
from backend.helpers.response_wrapper import ApiResponse
from backend.schemas.dashboard import DashboardStats
from backend.services import dashboard_service

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/stats", response_model=ApiResponse[DashboardStats])
async def dashboard_stats(
        session: AsyncSessionDep,
        _: AdminOnly = None
):
    stats = await dashboard_service.get_dashboard_stats(session)
    return ApiResponse(
        message="Dashboard stats retrieved successfully",
        meta_data=stats.model_dump()
    )