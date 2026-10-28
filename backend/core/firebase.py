import asyncio
from typing import Optional

import firebase_admin
import httpx
from fastapi import HTTPException
from firebase_admin import auth, credentials
from firebase_admin.exceptions import FirebaseError

from backend.core.configs import settings

_IDENTITY_TOOLKIT = "https://identitytoolkit.googleapis.com/v1/accounts"
_INVALID_CREDENTIALS = {"INVALID_LOGIN_CREDENTIALS", "EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_EMAIL"}


class _RestError(Exception):
    def __init__(self, message: str):
        self.message = message


def _ensure_app() -> None:
    if firebase_admin._apps:
        return
    if not settings.FIREBASE_SERVICE_ACCOUNT_PATH:
        raise HTTPException(status_code=503, detail="Firebase is not configured")
    firebase_admin.initialize_app(credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH))


def _web_api_key() -> str:
    if not settings.FIREBASE_WEB_API_KEY:
        raise HTTPException(status_code=503, detail="Firebase is not configured")
    return settings.FIREBASE_WEB_API_KEY


async def _admin_call(fn, *args, **kwargs):
    _ensure_app()
    try:
        return await asyncio.to_thread(fn, *args, **kwargs)
    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Email already registered in Firebase")
    except auth.PhoneNumberAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Phone number already registered in Firebase")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except auth.UserNotFoundError:
        raise
    except FirebaseError as e:
        raise HTTPException(status_code=502, detail=f"Firebase error: {e}")


async def _rest_call(endpoint: str, body: dict) -> dict:
    key = _web_api_key()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{_IDENTITY_TOOLKIT}:{endpoint}", params={"key": key}, json=body)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Firebase is unreachable")
    if response.is_success:
        return response.json()
    try:
        message = response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        message = ""
    raise _RestError(message)


async def verify_id_token(id_token: str) -> str:
    _ensure_app()
    try:
        decoded = await asyncio.to_thread(auth.verify_id_token, id_token, check_revoked=True)
    except auth.UserDisabledError:
        raise HTTPException(status_code=403, detail="User account is disabled")
    except (auth.InvalidIdTokenError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired Firebase ID token")
    except (auth.CertificateFetchError, FirebaseError):
        raise HTTPException(status_code=502, detail="Firebase verification failed")
    return decoded["uid"]


async def sign_in_with_password(email: str, password: str) -> str:
    try:
        data = await _rest_call("signInWithPassword", {"email": email, "password": password, "returnSecureToken": True})
    except _RestError as e:
        if e.message in _INVALID_CREDENTIALS:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if e.message.startswith("USER_DISABLED"):
            raise HTTPException(status_code=403, detail="User account is disabled")
        if e.message.startswith("TOO_MANY_ATTEMPTS_TRY_LATER"):
            raise HTTPException(status_code=429, detail="Too many attempts, try again later")
        raise HTTPException(status_code=502, detail="Firebase sign-in failed")
    return data["localId"]


async def send_password_reset_email(email: str) -> None:
    try:
        await _rest_call("sendOobCode", {"requestType": "PASSWORD_RESET", "email": email})
    except _RestError as e:
        if e.message.startswith("EMAIL_NOT_FOUND"):
            return
        raise HTTPException(status_code=502, detail="Firebase could not send the reset email")


async def create_user(email: str, password: Optional[str] = None, phone_number: Optional[str] = None) -> str:
    kwargs = {"email": email, "email_verified": True}
    if password:
        kwargs["password"] = password
    if phone_number:
        kwargs["phone_number"] = phone_number
    record = await _admin_call(auth.create_user, **kwargs)
    return record.uid


async def update_user(
    uid: str,
    *,
    email: Optional[str] = None,
    password: Optional[str] = None,
    phone_number: Optional[str] = None,
) -> None:
    kwargs = {}
    if email is not None:
        kwargs["email"] = email
    if password is not None:
        kwargs["password"] = password
    if phone_number is not None:
        kwargs["phone_number"] = phone_number
    if kwargs:
        await _admin_call(auth.update_user, uid, **kwargs)


async def delete_user(uid: str) -> None:
    try:
        await _admin_call(auth.delete_user, uid)
    except auth.UserNotFoundError:
        pass


async def revoke_refresh_tokens(uid: str) -> None:
    await _admin_call(auth.revoke_refresh_tokens, uid)


async def get_uid_by_email(email: str) -> Optional[str]:
    try:
        record = await _admin_call(auth.get_user_by_email, email)
    except auth.UserNotFoundError:
        return None
    return record.uid
