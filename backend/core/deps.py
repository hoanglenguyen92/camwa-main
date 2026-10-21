from typing import Annotated, List
from fastapi import Request

import jwt
from fastapi import HTTPException
from fastapi.params import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select

from backend.core.configs import settings
from backend.core.db import AsyncSessionDep
from backend.models import Iam

security = HTTPBearer()

async def get_current_user(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
        db: AsyncSessionDep,
) -> Iam:

    token = credentials.credentials

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        iam_id: str = payload.get("sub")
        token_version: int = payload.get("token_version")
        if iam_id is None or token_version is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


    result = await db.execute(select(Iam).where(Iam.iam_id == iam_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.token_version != token_version:
        raise HTTPException(status_code=401, detail="Token invalidated")

    return user


def require_role(allowed_roles: List[str]):
    def _role_checker(request: Request, current_user: Iam = Depends(get_current_user)):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
            jwt_role = payload.get("role")

            if jwt_role not in allowed_roles:
                raise HTTPException(status_code=403, detail=f"Role '{jwt_role}' not authorized. Requires: {allowed_roles}")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

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