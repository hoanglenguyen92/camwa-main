from fastapi import APIRouter, status, Depends

from backend.core.db import AsyncSessionDep
from backend.core.deps import get_current_user, CurrentUser
from backend.helpers.response_wrapper import ApiResponse
from backend.models import Iam
from backend.schemas.auth import TokenResponse, LoginRequest, RefreshResponse, RefreshRequest, MessageResponse
from backend.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=ApiResponse[TokenResponse], status_code=status.HTTP_200_OK)
async def login(payload: LoginRequest, db: AsyncSessionDep):
    """Authenticate user and return JWT tokens"""
    token = await auth_service.login(db, payload.email, payload.password)
    return ApiResponse(
        message="Login successful",
        meta_data=token
    )


@router.post("/refresh-token", response_model=ApiResponse[RefreshResponse])
async def refresh_token(payload: RefreshRequest, db: AsyncSessionDep):
    """Exchange valid refresh token for new access token"""
    token = await auth_service.refresh_access_token(db, payload.refresh_token)
    return ApiResponse(
        message="Token refreshed successfully",
        meta_data=token
    )


@router.post("/logout", response_model=ApiResponse)
async def logout(
    db: AsyncSessionDep,
    current_user: CurrentUser
):
    """Invalidate tokens and clear refresh token"""
    result = await auth_service.logout(db, current_user.iam_id)
    return ApiResponse(
        message="Logged out successfully",
        meta_data=result
    )

# @router.post("/toggle-role", response_model=TokenResponse)
# async def toggle_ac_role(
#     db: AsyncSessionDep,
#     current_user: Iam = Depends(get_current_user)
# ):
#     """Toggle Academic Coordinator between AC/LECTURER roles"""
#     return await auth_service.toggle_ac_role(db, current_user.iam_id)