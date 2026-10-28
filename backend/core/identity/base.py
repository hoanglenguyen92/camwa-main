"""Contract for external identity providers.

Every method returns or takes the provider's opaque user id (`auth_uid`). Failures are raised as
fastapi HTTPException: 401 bad credentials or token, 403 disabled user, 409 duplicate email or phone,
400 bad input, 429 throttled, 502 upstream failure, 503 provider not configured.
`delete_user` ignores unknown uids. `get_uid_by_email` returns None when absent.
"""
from typing import Optional, Protocol


class IdentityProvider(Protocol):
    async def sign_in_with_password(self, email: str, password: str) -> str: ...

    async def verify_token(self, token: str) -> str: ...

    async def send_password_reset_email(self, email: str) -> None: ...

    async def create_user(
        self, email: str, password: Optional[str] = None, phone_number: Optional[str] = None
    ) -> str: ...

    async def update_user(
        self,
        uid: str,
        *,
        email: Optional[str] = None,
        password: Optional[str] = None,
        phone_number: Optional[str] = None,
        clear_phone_number: bool = False,
    ) -> None: ...

    async def delete_user(self, uid: str) -> None: ...

    async def revoke_sessions(self, uid: str) -> None: ...

    async def get_uid_by_email(self, email: str) -> Optional[str]: ...
