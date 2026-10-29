from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.db import AsyncSessionDep
from backend.core.keycloak import keycloak, unauthorized
from backend.models import AcademicCoordinator, FacilityFaculty
from backend.models.enums import AccountRole

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    camwa_id: str
    roles: frozenset[AccountRole]
    acting: AccountRole
    program_id: Optional[str]
    claims: dict

    @property
    def is_admin(self) -> bool:
        return self.acting == AccountRole.ADMIN


def _base_role(roles: frozenset[AccountRole]) -> AccountRole:
    # AC is a composite of LECTURER, so an AC token carries both.
    if AccountRole.AC in roles and roles <= {AccountRole.AC, AccountRole.LECTURER}:
        return AccountRole.AC
    if len(roles) == 1:
        return next(iter(roles))
    raise HTTPException(status_code=403, detail="Your account needs exactly one CAMWA role")


async def get_principal(
    session: AsyncSessionDep,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer)],
) -> Principal:
    if credentials is None:
        raise unauthorized("Not authenticated")
    claims = await keycloak.verify_token(credentials.credentials)
    known = {role.value for role in AccountRole}
    roles = frozenset(AccountRole(r) for r in claims.get("realm_access", {}).get("roles", []) if r in known)
    role = _base_role(roles)
    camwa_id = claims["preferred_username"]
    acting, program_id = role, None
    if role == AccountRole.FA:
        staff = await session.get(FacilityFaculty, camwa_id)
        program_id = staff.program_id if staff else None
    elif role == AccountRole.AC:
        coordinator = await session.get(AcademicCoordinator, camwa_id)
        if coordinator:
            acting = AccountRole(coordinator.current_role.value)
            program_id = coordinator.program_id
    return Principal(camwa_id=camwa_id, roles=roles, acting=acting, program_id=program_id, claims=claims)


def require_role(*allowed: AccountRole):
    async def checker(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
        if principal.acting not in allowed:
            raise HTTPException(status_code=403, detail="Permission denied")
        if principal.acting in (AccountRole.FA, AccountRole.AC) and principal.program_id is None:
            raise HTTPException(status_code=403, detail="No staff profile found for your account")
        return principal
    return checker


ADMIN, FA, LECTURER, AC, STUDENT = AccountRole

CurrentUser = Annotated[Principal, Depends(get_principal)]
AllAuthenticated = Annotated[Principal, Depends(require_role(ADMIN, FA, LECTURER, AC, STUDENT))]
AdminOnly = Annotated[Principal, Depends(require_role(ADMIN))]
AdminOrFA = Annotated[Principal, Depends(require_role(ADMIN, FA))]
AdminOrFAOrAC = Annotated[Principal, Depends(require_role(ADMIN, FA, AC))]
AdminOrFAOrLecturer = Annotated[Principal, Depends(require_role(ADMIN, FA, LECTURER))]
AdminOrFAOrLecturerOrAC = Annotated[Principal, Depends(require_role(ADMIN, FA, LECTURER, AC))]
AdminOrFAOrLecturerOrStudent = Annotated[Principal, Depends(require_role(ADMIN, FA, LECTURER, STUDENT))]
AdminOrFAOrStudent = Annotated[Principal, Depends(require_role(ADMIN, FA, STUDENT))]
LecturerOrAC = Annotated[Principal, Depends(require_role(LECTURER, AC))]
StudentOnly = Annotated[Principal, Depends(require_role(STUDENT))]
