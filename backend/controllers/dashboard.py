from fastapi import APIRouter

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOnly
from backend.schemas.dashboard import DashboardStats
from backend.services import dashboard_service

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(session: AsyncSessionDep, _: AdminOnly):
    return await dashboard_service.get_dashboard_stats(session)
