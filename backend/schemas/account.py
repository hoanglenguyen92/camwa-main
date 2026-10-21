from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict

from backend.models.enums import AccountRole


class UserResponse(BaseModel):
    iam_id: str
    username: str
    email: EmailStr
    role: AccountRole

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    iam_id: str
    username: str
    email: EmailStr
    password: str
    role: AccountRole


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[AccountRole] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
