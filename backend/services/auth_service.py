import jwt
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.configs import settings
from backend.core import firebase
from backend.core.security import create_access_token, create_refresh_token, hash_token
from backend.models import Iam, AcademicCoordinator


async def _role_for_token(db: AsyncSession, user: Iam) -> str:
    if user.role != "AC":
        return user.role
    result = await db.execute(select(AcademicCoordinator).where(AcademicCoordinator.ac_id == user.iam_id))
    ac = result.scalars().first()
    return ac.current_role if ac else user.role


async def _issue_tokens(db: AsyncSession, user: Iam) -> dict:
    role_for_token = await _role_for_token(db, user)

    access_token = create_access_token(
        {"sub": user.iam_id, "email": user.email, "role": role_for_token, "username": user.username}, user.token_version
    )
    refresh_token = create_refresh_token({"sub": user.iam_id}, user.token_version)

    user.refresh_token = hash_token(refresh_token)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": role_for_token,
        "username": user.username
    }


async def _login_uid(db: AsyncSession, uid: str) -> dict:
    result = await db.execute(select(Iam).where(Iam.firebase_uid == uid))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=403, detail="No CAMWA account is linked to this Firebase user")

    return await _issue_tokens(db, user)


async def login_with_password(db: AsyncSession, email: str, password: str) -> dict:
    uid = await firebase.sign_in_with_password(email, password)
    return await _login_uid(db, uid)


async def login_with_id_token(db: AsyncSession, id_token: str) -> dict:
    uid = await firebase.verify_id_token(id_token)
    return await _login_uid(db, uid)


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
        Iam.refresh_token == hash_token(refresh_token),
        Iam.token_version == token_version
    )
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    role_for_token = await _role_for_token(db, user)

    new_access = create_access_token(
        {'sub': user.iam_id, 'email': user.email, 'role': role_for_token, 'username': user.username}, user.token_version
    )
    return {"access_token": new_access}


async def logout(db: AsyncSession, user: Iam) -> None:
    await db.execute(
        update(Iam).where(Iam.iam_id == user.iam_id).values(token_version = Iam.token_version + 1, refresh_token = None)
    )
    await db.commit()
    await firebase.revoke_refresh_tokens(user.firebase_uid)


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
        update(Iam).where(Iam.iam_id == user_id).values(refresh_token=hash_token(new_refresh))
    )
    await db.commit()

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "role": new_role,
        "username": user.username,
        "message": f"Role toggled to {new_role}"
    }