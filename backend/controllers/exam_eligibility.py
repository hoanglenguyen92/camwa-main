from typing import Optional

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOrFAOrLecturer, AdminOrFAOrLecturerOrAC, Principal
from backend.core.policies import module_scope
from backend.models import Module
from backend.schemas.attendance import EligibilityRecalculation
from backend.services import attendance_service

router = APIRouter(
    prefix="/exam-eligibility",
    tags=["ExamEligibility"],
)

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def _modules_in_reach(
    user: Principal, session: AsyncSession, module_id: Optional[str], lecturer_id: Optional[str]
) -> list[str]:
    stmt = select(Module.module_id).where(module_scope(user, Module.module_id))
    if module_id:
        stmt = stmt.where(Module.module_id == module_id)
    if lecturer_id:
        stmt = stmt.where(Module.lecturer_id == lecturer_id)
    module_ids = list((await session.execute(stmt)).scalars().all())
    if module_id and not module_ids:
        raise HTTPException(status_code=404, detail="Module not found")
    return module_ids


@router.post("/recalculations")
async def recalculate_exam_eligibility(session: AsyncSessionDep, data: EligibilityRecalculation, user: AdminOrFAOrLecturer):
    module_ids = await _modules_in_reach(user, session, data.module_id, data.lecturer_id)
    return await attendance_service.recalculate_exam_eligibility(session, module_ids)


@router.get(
    "/export",
    response_class=Response,
    responses={200: {"content": {XLSX: {}}, "description": "One sheet per module."}},
)
async def export_exam_eligibility(
    session: AsyncSessionDep,
    user: AdminOrFAOrLecturerOrAC,
    module_id: Optional[str] = None,
    lecturer_id: Optional[str] = None,
):
    module_ids = await _modules_in_reach(user, session, module_id, lecturer_id)
    contents = await attendance_service.export_exam_eligibility(session, module_ids)
    return Response(
        content=contents,
        media_type=XLSX,
        headers={"Content-Disposition": 'attachment; filename="exam-eligibility.xlsx"'},
    )
