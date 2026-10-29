from typing import Optional

from pydantic import BaseModel

from backend.models.enums import AccountRole, CoordinatorRole


class MeResponse(BaseModel):
    camwa_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    roles: list[AccountRole]
    acting_role: AccountRole
    program_id: Optional[str] = None
    has_profile: bool


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class ActingRole(BaseModel):
    role: CoordinatorRole
