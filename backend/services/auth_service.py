import math
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.configs import settings
from backend.core.security import verify_password, create_access_token, create_refresh_token
from backend.models import Iam, AcademicCoordinator


async def login(db: AsyncSession, email: str, password: str) -> dict:
    result = await db.execute(select(Iam).where(Iam.email == email))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.locked_until and user.locked_until > datetime.now():
        raise HTTPException(status_code=401, detail=f"Too many failed login attempts. Your account is locked until {user.locked_until.isoformat()}")

    if not verify_password(password, user.password):
        user.failed_attempts += 1
        user.last_attempt_at = datetime.now()

        if user.failed_attempts >= 5:
            lockout_exponent = user.failed_attempts - 4
            lockout_minutes = math.pow(5, lockout_exponent)
            user.locked_until = datetime.now() + timedelta(minutes=lockout_minutes)

        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid password")

    user.failed_attempts = 0
    user.locked_until = None
    await db.commit()


    role_for_token = user.role
    if user.role == "AC":
        ac_stmt = select(AcademicCoordinator).where(AcademicCoordinator.ac_id == user.iam_id)
        ac_result = await db.execute(ac_stmt)
        ac = ac_result.scalars().first()
        if ac:
            role_for_token = ac.current_role

    access_token = create_access_token(
        {"sub": user.iam_id, "email": user.email, "role": role_for_token, "username": user.username}, user.token_version
    )
    refresh_token = create_refresh_token({"sub": user.iam_id}, user.token_version)

    user.refresh_token = refresh_token
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": role_for_token,
        "username": user.username
    }


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> dict:
    try:
        payload = jwt.decode(refresh_token, settings.JWT_REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    token_version = payload.get("token_version")

    stmt = select(Iam).where(
        Iam.iam_id == user_id,
        Iam.refresh_token == refresh_token,
        Iam.token_version == token_version
    )
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    role_for_token = user.role
    if user.role == "AC":
        ac_stmt = select(AcademicCoordinator).where(AcademicCoordinator.ac_id == user.iam_id)
        ac_result = await db.execute(ac_stmt)
        ac = ac_result.scalars().first()

        if ac:
            role_for_token = ac.current_role

    new_access = create_access_token(
        {'sub': user.iam_id, 'email': user.email, 'role': role_for_token, 'username': user.username}, user.token_version
    )
    return {"access_token": new_access}


async def logout(db: AsyncSession, user_id: str) -> None:
    await db.execute(
        update(Iam).where(Iam.iam_id == user_id).values(token_version = Iam.token_version + 1, refresh_token = None)
    )
    await db.commit()


async def toggle_ac_role(db: AsyncSession, user_id: str) -> dict:
    stmt = select(Iam).where(Iam.iam_id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != "AC":
        raise HTTPException(status_code=403, detail="Only Academic Coordinators can toggle roles")

    ac_stmt = select(AcademicCoordinator).where(AcademicCoordinator.ac_id == user_id)
    ac_result = await db.execute(ac_stmt)
    ac = ac_result.scalars().first()
    if not ac:
        raise HTTPException(status_code=404, detail="Academic Coordinator not found")

    new_role = "LECTURER" if ac.current_role == "AC" else "AC"
    ac.current_role = new_role

    await db.execute(
        update(Iam).where(Iam.iam_id == user_id).values(token_version=Iam.token_version + 1, refresh_token=None)
    )
    await db.commit()

    new_access = create_access_token(
        {"sub": user.iam_id, "email": user.email, "role": new_role, "username": user.username}, user.token_version + 1
    )

    new_refresh = create_refresh_token({"sub": user.iam_id}, user.token_version + 1)
    await db.execute(
        update(Iam).where(Iam.iam_id == user_id).values(refresh_token=new_refresh)
    )
    await db.commit()

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "role": new_role,
        "username": user.username,
        "message": f"Role toggled to {new_role}"
    }