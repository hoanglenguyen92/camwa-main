from typing import List

from fastapi import APIRouter, status, HTTPException, UploadFile, File

from backend.core.db import AsyncSessionDep
from backend.core.deps import CurrentUser, AdminOrFA, AdminOnly

from backend.helpers.response_wrapper import ApiResponse
from backend.schemas.account import UserResponse, UserCreate, UserUpdate, PasswordChange
from backend.services import account_service

router = APIRouter(
    prefix="/account",
    tags=["Account"],
)


@router.post("/create", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, session: AsyncSessionDep, _: AdminOrFA):
    user = await account_service.create_user(session, data)
    return ApiResponse(
        message="User created successfully",
        meta_data=user
    )


@router.post("/students/create-from-excel", response_model=ApiResponse[dict])
async def import_students(session: AsyncSessionDep, file: UploadFile = File(...), _: AdminOnly = None):
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in [".xlsx", ".xls"]):
        raise HTTPException(status_code=400, detail="Invalid file type. Only Excel files are allowed.")

    contents = await file.read()
    result = await account_service.create_multiple_students_from_excel(session, contents)
    return ApiResponse(
        message="Students imported successfully",
        meta_data=result
    )


@router.post("/lecturers/create-from-excel", response_model=ApiResponse[dict])
async def import_lecturers(session: AsyncSessionDep, file: UploadFile = File(...), _: AdminOnly = None):
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in [".xlsx", ".xls"]):
        raise HTTPException(status_code=400, detail="Invalid file type. Only Excel files are allowed.")

    contents = await file.read()
    result = await account_service.create_multiple_lecturers_from_excel(session, contents)
    return ApiResponse(
        message="Lecturers imported successfully",
        meta_data=result
    )


@router.get("/", response_model=ApiResponse[List[UserResponse]])
async def get_all_users(session: AsyncSessionDep, _: CurrentUser):
    users = await account_service.get_all_users(session)
    return ApiResponse(
        message="Users retrieved successfully",
        meta_data=users
    )


@router.get("/{iam_id}", response_model=ApiResponse[UserResponse])
async def get_user_by_id(iam_id: str, session: AsyncSessionDep, _: CurrentUser):
    user = await account_service.get_user_by_id(session, iam_id)
    return ApiResponse(
        message="User retrieved successfully",
        meta_data=user
    )


@router.put("/{iam_id}", response_model=ApiResponse[UserResponse])
async def update_user(data: UserUpdate, iam_id: str, session: AsyncSessionDep, user: CurrentUser):
    if user.role != "ADMIN" and user.iam_id != iam_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this user.",
        )

    update = await account_service.update_user(session, iam_id, data)
    return ApiResponse(
        message="User updated successfully",
        meta_data=update
    )


@router.put("/{iam_id}/change-password", response_model=ApiResponse[None])
async def change_password(iam_id: str, data: PasswordChange, session: AsyncSessionDep, user: CurrentUser,):
    if user.role != "ADMIN" and user.iam_id != iam_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to change this password.",
        )

    await account_service.change_password(session, iam_id, data)
    return ApiResponse(
        message="Password changed successfully",
        meta_data=None
    )


@router.delete("/{iam_id}", response_model=None)
async def delete_user(iam_id: str, session: AsyncSessionDep, _: AdminOrFA,):
    await account_service.delete_user(session, iam_id)
    return ApiResponse(
        message="User deleted successfully",
        meta_data=None
    )





