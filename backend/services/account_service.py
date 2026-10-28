import io
import logging
from typing import List

import openpyxl
from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.identity import provider as identity
from backend.core.security import invalidate_user_tokens
from backend.models import Iam, ImageAsset
from backend.schemas.account import UserResponse, UserCreate, UserUpdate, PasswordChange

logger = logging.getLogger(__name__)

'''CRUD Operations for Users'''

async def create_user(session: AsyncSession, data: UserCreate) -> UserResponse:
    conditions = [Iam.email == data.email, Iam.username == data.username]
    if data.phone_number:
        conditions.append(Iam.phone_number == data.phone_number)
    existing_user = await session.execute(select(Iam).where(or_(*conditions)))
    if existing_user.scalar():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"User with {data.username}, {data.email} or that phone number already exists")

    uid = await identity.create_user(data.email, data.password, data.phone_number)
    new_user = Iam(
        iam_id=data.iam_id,
        username=data.username,
        email=data.email,
        auth_uid=uid,
        phone_number=data.phone_number,
        role=data.role.value,
    )
    session.add(new_user)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        await identity.delete_user(uid)
        raise
    await session.refresh(new_user)
    return UserResponse.model_validate(new_user)


async def get_all_users(session: AsyncSession) -> List[UserResponse]:
    result = await session.execute(select(Iam))
    users = result.scalars().all()
    return [UserResponse.model_validate(user) for user in users]


async def get_user_by_id(session: AsyncSession, iam_id: str) -> UserResponse:
    user = await session.get(Iam, iam_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with {iam_id} not found")
    return UserResponse.model_validate(user)


async def update_user(session: AsyncSession, iam_id: str, data: UserUpdate) -> UserResponse:
    user = await session.get(Iam, iam_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with {iam_id} not found")

    update_dict = data.model_dump(exclude_unset=True)

    if not update_dict:
        return UserResponse.model_validate(user)

    if "email" in update_dict and update_dict["email"] != user.email:
        existing_user = await session.execute(
            select(Iam).where(Iam.email == update_dict["email"])
        )
        if existing_user.scalar():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"User with {update_dict['email']} already exists")

    if "username" in update_dict and update_dict["username"] != user.username:
        existing_user = await session.execute(
            select(Iam).where(Iam.username == update_dict["username"], Iam.iam_id != iam_id)
        )
        if existing_user.scalar():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with username {update_dict['username']} already exists",
            )

    if "phone_number" in update_dict and update_dict["phone_number"] != user.phone_number:
        if update_dict["phone_number"]:
            existing_user = await session.execute(
                select(Iam).where(Iam.phone_number == update_dict["phone_number"], Iam.iam_id != iam_id)
            )
            if existing_user.scalar():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with that phone number already exists")

    uid, old_email, old_phone = user.auth_uid, user.email, user.phone_number
    password = update_dict.pop("password", None) or None
    if password or ("role" in update_dict and update_dict["role"] != user.role):
        user.token_version += 1
    await identity.update_user(
        uid,
        email=update_dict.get("email"),
        password=password,
        phone_number=update_dict.get("phone_number"),
        clear_phone_number="phone_number" in update_dict and update_dict["phone_number"] is None,
    )

    for field, value in update_dict.items():
        setattr(user, field, value)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        try:
            await identity.update_user(
                uid, email=old_email, phone_number=old_phone, clear_phone_number=old_phone is None
            )
        except Exception:
            pass
        raise
    if password:
        await identity.revoke_sessions(uid)
    await session.refresh(user)
    return UserResponse.model_validate(user)


async def delete_user(session: AsyncSession, iam_id: str) -> None:
    user = await session.get(Iam, iam_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with {iam_id} not found")
    uid = user.auth_uid
    await session.delete(user)
    await session.commit()
    try:
        await identity.delete_user(uid)
    except HTTPException:
        logger.warning("Deleted iam %s but could not delete identity user %s", iam_id, uid)


async def change_password(session: AsyncSession, iam_id: str, data: PasswordChange) -> None:
    user = await session.get(Iam, iam_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with {iam_id} not found")

    try:
        await identity.sign_in_with_password(user.email, data.current_password)
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        raise
    if data.new_password == data.current_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password cannot be the same as the current password")

    await identity.update_user(user.auth_uid, password=data.new_password)
    await invalidate_user_tokens(session, iam_id)

'''Bulk Operations for Users'''

async def _process_excel(session: AsyncSession, file_contents: bytes, role: str):
    workbook = openpyxl.load_workbook(io.BytesIO(file_contents))
    sheet = workbook.active
    successful = []
    failed = []
    created_uids = []
    seen_iam_ids = set()
    seen_usernames = set()
    seen_emails = set()
    for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if not row or not row[0] or not row[1]:
            continue
        iam_id = str(row[0]).strip()
        email = str(row[1]).strip()
        username = str(row[2]).strip() if len(row) > 2 and row[2] else iam_id
        password = str(row[3]).strip() if len(row) > 3 and row[3] else None
        if iam_id in seen_iam_ids or username in seen_usernames or email in seen_emails:
            failed.append({
                "row": row_index,
                "iam_id": iam_id,
                "username": username,
                "email": email,
                "error": "Duplicate user in Excel file",
            })
            continue
        seen_iam_ids.add(iam_id)
        seen_usernames.add(username)
        seen_emails.add(email)
        existing = await session.execute(
            select(Iam).where(
                or_(
                    Iam.iam_id == iam_id,
                    Iam.username == username,
                    Iam.email == email,
                )
            )
        )
        if existing.scalar():
            failed.append({
                "row": row_index,
                "iam_id": iam_id,
                "username": username,
                "email": email,
                "error": "User already exists",
            })
            continue
        try:
            uid = await identity.create_user(email, password)
        except HTTPException as e:
            failed.append({
                "row": row_index,
                "iam_id": iam_id,
                "username": username,
                "email": email,
                "error": e.detail,
            })
            continue
        created_uids.append(uid)
        new_user = Iam(
            iam_id=iam_id,
            username=username,
            email=email,
            auth_uid=uid,
            role=role,
        )
        session.add(new_user)
        if role == "STUDENT":
            session.add(
                ImageAsset(
                    iam_id=iam_id,
                    image_path=f"image_assets/{username}.jpg",
                )
            )
        successful.append({
            "iam_id": iam_id,
            "username": username,
            "email": email,
            "password_set": password is not None,
        })
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        for uid in created_uids:
            await identity.delete_user(uid)
        raise
    return {
        "successful": successful,
        "failed": failed,
    }


async def create_multiple_students_from_excel(session: AsyncSession, file_contents: bytes):
    return await _process_excel(session, file_contents, role="STUDENT")


async def create_multiple_lecturers_from_excel(session: AsyncSession, file_contents: bytes):
    return await _process_excel(session, file_contents, role="LECTURER")
