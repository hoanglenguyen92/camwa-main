from fastapi import APIRouter, BackgroundTasks

from backend.core.deps import AllAuthenticated
from backend.core.keycloak import keycloak
from backend.schemas.auth import LoginRequest, PasswordResetRequest, RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    return TokenResponse.model_validate(await keycloak.login(data.email, data.password))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest):
    return TokenResponse.model_validate(await keycloak.refresh(data.refresh_token))


@router.post("/logout", status_code=204)
async def logout(data: RefreshRequest, _: AllAuthenticated):
    await keycloak.logout(data.refresh_token)


@router.post("/password-reset", status_code=202)
async def request_password_reset(data: PasswordResetRequest, background: BackgroundTasks):
    # Runs after the response, so timing doesn't reveal whether the email has an account.
    background.add_task(keycloak.send_password_reset, data.email)
