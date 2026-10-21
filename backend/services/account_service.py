import io
from typing import List

import openpyxl
from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import pwd_context
from backend.models import Iam, ImageAsset
from backend.schemas.account import UserResponse, UserCreate, UserUpdate, PasswordChange

'''CRUD Operations for Users'''

async def create_user(session: AsyncSession, data: UserCreate) -> UserResponse:
    existing_user = await session.execute(
        select(Iam).where(or_(Iam.email == data.email, Iam.username == data.username))
    )
    if existing_user.scalar():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"User with {data.username} or {data.email} already exists")

    hashed_password = pwd_context.hash(data.password)
    new_user = Iam(
        iam_id=data.iam_id,
        username=data.username,
        email=data.email,
        password=hashed_password,
        role=data.role.value,
    )
    session.add(new_user)
    await session.commit()
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

    if "password" in update_dict and update_dict["password"]:
        update_dict["password"] = pwd_context.hash(update_dict["password"])


    for field, value in update_dict.items():
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)


async def delete_user(session: AsyncSession, iam_id: str) -> None:
    user = await session.get(Iam, iam_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with {iam_id} not found")
    await session.delete(user)
    await session.commit()


async def change_password(session: AsyncSession, iam_id: str, data: PasswordChange) -> None:
    user = await session.get(Iam, iam_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with {iam_id} not found")

    if not pwd_context.verify(data.current_password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if pwd_context.verify(data.new_password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password cannot be the same as the current password")

    user.password = pwd_context.hash(data.new_password)
    await session.commit()

'''Bulk Operations for Users'''

async def _process_excel(session: AsyncSession, file_contents: bytes, role: str):
    workbook = openpyxl.load_workbook(io.BytesIO(file_contents))
    sheet = workbook.active
    successful = []
    failed = []
    seen_iam_ids = set()
    seen_usernames = set()
    seen_emails = set()
    for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if not row or not row[0] or not row[1]:
            continue
        iam_id = str(row[0]).strip()
        email = str(row[1]).strip()
        username = str(row[2]).strip() if len(row) > 2 and row[2] else iam_id
        password = str(row[3]).strip() if len(row) > 3 and row[3] else iam_id
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
        new_user = Iam(
            iam_id=iam_id,
            username=username,
            email=email,
            password=pwd_context.hash(password),
            role=role,
        )
        session.add(new_user)
        if role == "STUDENT":
            session.add(
                ImageAsset(
                    username=username,
                    image_path=f"image_assets/{username}.jpg",
                )
            )
        successful.append({
            "iam_id": iam_id,
            "username": username,
            "email": email,
        })
    await session.commit()
    return {
        "successful": successful,
        "failed": failed,
    }


async def create_multiple_students_from_excel(session: AsyncSession, file_contents: bytes):
    return await _process_excel(session, file_contents, role="STUDENT")


async def create_multiple_lecturers_from_excel(session: AsyncSession, file_contents: bytes):
    return await _process_excel(session, file_contents, role="LECTURER")
