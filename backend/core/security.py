from datetime import timedelta, datetime, timezone
from typing import Optional

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.configs import settings
from backend.models import Iam

def create_access_token(data: dict, token_version: int) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "token_version": token_version,
        "iat": datetime.now(timezone.utc)
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict, token_version: int) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "token_version": token_version,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)


async def invalidate_user_tokens(db: AsyncSession, iam_id: str):
    await db.execute(update(Iam).where(Iam.iam_id == iam_id).values(token_version=Iam.token_version + 1))
    await db.commit()
