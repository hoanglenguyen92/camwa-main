from typing import Annotated, List

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select

from backend.core.configs import settings
from backend.core.db import AsyncSessionDep
from backend.models import Iam

security = HTTPBearer()


async def get_token_payload(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("sub") is None or payload.get("token_version") is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


TokenPayload = Annotated[dict, Depends(get_token_payload)]


async def get_current_user(payload: TokenPayload, db: AsyncSessionDep) -> Iam:
    result = await db.execute(select(Iam).where(Iam.iam_id == payload["sub"]))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.token_version != payload["token_version"]:
        raise HTTPException(status_code=401, detail="Token invalidated")

    return user


def require_role(allowed_roles: List[str]):
    def _role_checker(payload: TokenPayload, current_user: Iam = Depends(get_current_user)):
        jwt_role = payload.get("role")
        if jwt_role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Role '{jwt_role}' not authorized. Requires: {allowed_roles}")
        return current_user
    return _role_checker


AdminOnly = Annotated[Iam, Depends(require_role(["ADMIN"]))]
AdminOrFA = Annotated[Iam, Depends(require_role(["ADMIN", "FA"]))]
AdminOrFAOrAC = Annotated[Iam, Depends(require_role(["ADMIN", "FA", "AC"]))]
AdminOrFAOrLecturer = Annotated[Iam, Depends(require_role(["ADMIN", "FA", "LECTURER"]))]
AdminOrFAOrLecturerOrAC = Annotated[Iam, Depends(require_role(["ADMIN", "FA", "LECTURER", "AC"]))]
LecturerOnly = Annotated[Iam, Depends(require_role(["LECTURER"]))]
StudentOnly = Annotated[Iam, Depends(require_role(["STUDENT"]))]
AllAuthenticated = Annotated[Iam, Depends(require_role(["ADMIN", "FA", "LECTURER", "STUDENT", "AC"]))]

CurrentUser = Annotated[Iam, Depends(get_current_user)]