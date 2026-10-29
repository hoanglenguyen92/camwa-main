from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOnly
from backend.helpers.http import read_upload
from backend.schemas.users import UserAccountResponse, UserImportReport, UserStatusUpdate
from backend.services import user_service

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.post("/imports", response_model=UserImportReport)
async def import_users(session: AsyncSessionDep, _: AdminOnly, file: UploadFile = File(...)):
    contents = await read_upload(file, ".csv")
    return await user_service.import_users(session, contents)


@router.get("/{camwa_id}", response_model=UserAccountResponse)
async def get_user(camwa_id: str, _: AdminOnly):
    return await user_service.get_account(camwa_id)


@router.patch("/{camwa_id}", response_model=UserAccountResponse)
async def update_user(camwa_id: str, data: UserStatusUpdate, user: AdminOnly):
    if camwa_id == user.camwa_id and not data.active:
        raise HTTPException(status_code=409, detail="You can't deactivate your own account")
    return await user_service.set_account_active(camwa_id, data.active)
