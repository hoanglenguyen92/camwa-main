from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict, Field

from backend.models.enums import AccountRole

E164 = r"^\+[1-9]\d{6,14}$"


class UserResponse(BaseModel):
    iam_id: str
    username: str
    email: EmailStr
    role: AccountRole
    phone_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    iam_id: str
    username: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = Field(default=None, pattern=E164)
    role: AccountRole


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    phone_number: Optional[str] = Field(default=None, pattern=E164)
    role: Optional[AccountRole] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
