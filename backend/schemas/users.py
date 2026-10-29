from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from backend.models.enums import AccountRole

E164 = r"^\+[1-9]\d{6,14}$"
IMPORTABLE_ROLES = (AccountRole.FA, AccountRole.LECTURER, AccountRole.AC, AccountRole.STUDENT)


class UserImportRow(BaseModel):
    camwa_id: str = Field(pattern=r"^[0-9]{1,20}$")
    email: EmailStr
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    role: AccountRole
    program_id: str = Field(min_length=1)
    intake: Optional[int] = None
    phone_number: Optional[str] = Field(default=None, pattern=E164)

    @field_validator("intake", "phone_number", mode="before")
    @classmethod
    def _blank_is_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("role")
    @classmethod
    def _importable(cls, role: AccountRole) -> AccountRole:
        if role not in IMPORTABLE_ROLES:
            raise ValueError("ADMIN accounts are made only in the Keycloak console")
        return role

    @model_validator(mode="after")
    def _student_needs_intake(self):
        if self.role == AccountRole.STUDENT and self.intake is None:
            raise ValueError("intake is required for STUDENT")
        return self

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class UserImportRowResult(BaseModel):
    row: int
    camwa_id: str
    outcome: Literal["created", "skipped", "failed"]
    reason: Optional[str] = None


class UserImportReport(BaseModel):
    created: int
    skipped: int
    failed: int
    rows: list[UserImportRowResult]


class UserAccountResponse(BaseModel):
    camwa_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    active: bool
    model_config = {"from_attributes": True}


class UserStatusUpdate(BaseModel):
    active: bool
