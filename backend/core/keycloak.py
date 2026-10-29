import time
from dataclasses import dataclass
from typing import Optional

import httpx
import jwt
from fastapi import HTTPException

from backend.core.configs import settings

UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}
_JWKS_MIN_REFRESH_SECONDS = 30


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int


@dataclass(frozen=True)
class UserAccount:
    id: str
    camwa_id: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone_number: Optional[str]
    active: bool


@dataclass(frozen=True)
class NewUser:
    camwa_id: str
    email: str
    first_name: str
    last_name: str
    role: str
    phone_number: Optional[str] = None


class UserExists(Exception):
    pass


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers=UNAUTHORIZED_HEADERS)


def _account(rep: dict) -> UserAccount:
    phone = (rep.get("attributes") or {}).get("phone_number") or [None]
    return UserAccount(
        id=rep["id"],
        camwa_id=rep["username"],
        email=rep.get("email"),
        first_name=rep.get("firstName"),
        last_name=rep.get("lastName"),
        phone_number=phone[0],
        active=rep.get("enabled", False),
    )


def _token_set(data: dict) -> TokenSet:
    return TokenSet(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_in=data["expires_in"],
        refresh_expires_in=data.get("refresh_expires_in", 0),
    )


class KeycloakClient:
    """The only code that talks to Keycloak: OIDC grants, token verification and the admin API."""

    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.transport = transport
        self._http: Optional[httpx.AsyncClient] = None
        self._keys: dict[str, jwt.PyJWK] = {}
        self._keys_fetched_at = 0.0
        self._admin_token: Optional[str] = None
        self._admin_token_expires_at = 0.0

    @property
    def _oidc(self) -> str:
        return f"{settings.keycloak_issuer}/protocol/openid-connect"

    @property
    def _admin(self) -> str:
        return f"{settings.KEYCLOAK_URL.rstrip('/')}/admin/realms/{settings.KEYCLOAK_REALM}"

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(transport=self.transport, timeout=settings.KEYCLOAK_TIMEOUT_SECONDS)
        return self._http

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            return await self._client().request(method, url, **kwargs)
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="Keycloak is unreachable")

    async def _grant(self, **form) -> httpx.Response:
        return await self._request(
            "POST",
            f"{self._oidc}/token",
            data={"client_id": settings.KEYCLOAK_CLIENT_ID, "client_secret": settings.KEYCLOAK_CLIENT_SECRET, **form},
        )

    async def login(self, username: str, password: str) -> TokenSet:
        response = await self._grant(grant_type="password", username=username, password=password, scope="openid")
        if response.is_success:
            return _token_set(response.json())
        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        if body.get("error") == "invalid_grant":
            if "not fully set up" in body.get("error_description", ""):
                raise HTTPException(status_code=403, detail="Set your password from the email we sent")
            raise unauthorized("Invalid email or password")
        raise HTTPException(status_code=502, detail="Keycloak sign-in failed")

    async def refresh(self, refresh_token: str) -> TokenSet:
        response = await self._grant(grant_type="refresh_token", refresh_token=refresh_token)
        if response.is_success:
            return _token_set(response.json())
        if response.status_code in (400, 401):
            raise unauthorized("Session expired, sign in again")
        raise HTTPException(status_code=502, detail="Keycloak refresh failed")

    async def logout(self, refresh_token: str) -> None:
        response = await self._request(
            "POST",
            f"{self._oidc}/logout",
            data={
                "client_id": settings.KEYCLOAK_CLIENT_ID,
                "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                "refresh_token": refresh_token,
            },
        )
        if response.status_code >= 500:
            raise HTTPException(status_code=502, detail="Keycloak logout failed")

    async def _signing_key(self, kid: str) -> jwt.PyJWK:
        stale = time.monotonic() - self._keys_fetched_at > _JWKS_MIN_REFRESH_SECONDS
        if kid not in self._keys and stale:
            response = await self._request("GET", f"{self._oidc}/certs")
            if not response.is_success:
                raise HTTPException(status_code=502, detail="Keycloak keys are unavailable")
            key_set = jwt.PyJWKSet.from_dict(response.json())
            self._keys = {key.key_id: key for key in key_set.keys if key.key_id}
            self._keys_fetched_at = time.monotonic()
        if kid not in self._keys:
            raise unauthorized("Invalid token")
        return self._keys[kid]

    async def verify_token(self, token: str) -> dict:
        try:
            kid = jwt.get_unverified_header(token).get("kid")
        except jwt.PyJWTError:
            raise unauthorized("Invalid token")
        if not kid:
            raise unauthorized("Invalid token")
        key = await self._signing_key(kid)
        try:
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256"],
                audience=settings.KEYCLOAK_CLIENT_ID,
                issuer=settings.keycloak_issuer,
                options={"require": ["exp", "iat", "iss", "aud", "preferred_username"]},
            )
        except jwt.ExpiredSignatureError:
            raise unauthorized("Token expired")
        except jwt.PyJWTError:
            raise unauthorized("Invalid token")
        if claims.get("azp") != settings.KEYCLOAK_CLIENT_ID:
            raise unauthorized("Invalid token")
        return claims

    async def _admin_headers(self) -> dict:
        if self._admin_token is None or time.monotonic() >= self._admin_token_expires_at:
            response = await self._grant(grant_type="client_credentials")
            if not response.is_success:
                raise HTTPException(status_code=502, detail="Keycloak admin sign-in failed")
            data = response.json()
            self._admin_token = data["access_token"]
            self._admin_token_expires_at = time.monotonic() + data["expires_in"] - 30
        return {"Authorization": f"Bearer {self._admin_token}"}

    async def _admin_call(self, method: str, path: str, ok: tuple[int, ...] = (200, 201, 204), **kwargs) -> httpx.Response:
        response = await self._request(method, f"{self._admin}{path}", headers=await self._admin_headers(), **kwargs)
        if response.status_code not in ok:
            raise HTTPException(status_code=502, detail=f"Keycloak admin call failed ({response.status_code})")
        return response

    async def _find_rep(self, **query) -> Optional[dict]:
        response = await self._admin_call("GET", "/users", params={**query, "exact": "true", "briefRepresentation": "false"})
        return next(iter(response.json()), None)

    async def get_user(self, camwa_id: str) -> Optional[UserAccount]:
        rep = await self._find_rep(username=camwa_id)
        return _account(rep) if rep else None

    async def list_users(self, batch: int = 500) -> list[UserAccount]:
        users: list[UserAccount] = []
        while True:
            response = await self._admin_call(
                "GET", "/users", params={"first": len(users), "max": batch, "briefRepresentation": "false"}
            )
            page = response.json()
            users.extend(_account(rep) for rep in page)
            if len(page) < batch:
                return users

    async def find_user_by_email(self, email: str) -> Optional[UserAccount]:
        rep = await self._find_rep(email=email)
        return _account(rep) if rep else None

    async def create_user(self, user: NewUser) -> UserAccount:
        rep = {
            "username": user.camwa_id,
            "email": user.email,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "enabled": True,
            "emailVerified": True,
            "attributes": {"phone_number": [user.phone_number]} if user.phone_number else {},
        }
        response = await self._admin_call("POST", "/users", ok=(201, 409), json=rep)
        if response.status_code == 409:
            raise UserExists()
        user_id = response.headers["Location"].rstrip("/").rsplit("/", 1)[-1]
        role = (await self._admin_call("GET", f"/roles/{user.role}")).json()
        await self._admin_call("POST", f"/users/{user_id}/role-mappings/realm", json=[role])
        return UserAccount(
            id=user_id,
            camwa_id=user.camwa_id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
            active=True,
        )

    async def send_set_password_email(self, user_id: str) -> None:
        await self._admin_call(
            "PUT",
            f"/users/{user_id}/execute-actions-email",
            params={"client_id": settings.KEYCLOAK_CLIENT_ID},
            json=["UPDATE_PASSWORD"],
        )

    async def send_password_reset(self, email: str) -> None:
        user = await self.find_user_by_email(email)
        if user and user.active:
            await self.send_set_password_email(user.id)

    async def set_active(self, user_id: str, active: bool) -> None:
        rep = (await self._admin_call("GET", f"/users/{user_id}")).json()
        if rep.get("enabled") != active:
            rep["enabled"] = active
            await self._admin_call("PUT", f"/users/{user_id}", json=rep)
        if not active:
            await self.end_sessions(user_id)

    async def end_sessions(self, user_id: str) -> None:
        await self._admin_call("POST", f"/users/{user_id}/logout")

    async def set_password(self, user_id: str, password: str) -> None:
        response = await self._admin_call(
            "PUT",
            f"/users/{user_id}/reset-password",
            ok=(204, 400),
            json={"type": "password", "value": password, "temporary": False},
        )
        if response.status_code == 400:
            detail = response.json().get("error_description") or response.json().get("error") or "Password rejected"
            raise HTTPException(status_code=422, detail=detail)


keycloak = KeycloakClient()
