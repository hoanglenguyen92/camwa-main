from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.core.db import AsyncSessionDep
from backend.core.deps import AllAuthenticated, CurrentUser, LecturerOrAC, StudentOnly
from backend.core.keycloak import keycloak
from backend.core.policies import notification_scope
from backend.helpers.pagination import Page, PageDep
from backend.models import AcademicCoordinator, FacilityFaculty, Lecturer, ModuleRegistration, Student
from backend.models.enums import AccountRole, NotificationStatus
from backend.schemas.auth import TokenResponse
from backend.schemas.me import ActingRole, MeResponse, PasswordChange
from backend.schemas.module_registration import LecturerStudentsAttendanceResponse, ModuleRegistrationResponse
from backend.schemas.notification import NotificationCount, NotificationResponse, NotificationStatusUpdate
from backend.services import module_registration_service, notification_service, student_service

router = APIRouter(
    prefix="/me",
    tags=["Me"],
)

_PROFILE_MODEL = {
    AccountRole.STUDENT: Student,
    AccountRole.LECTURER: Lecturer,
    AccountRole.AC: AcademicCoordinator,
    AccountRole.FA: FacilityFaculty,
}


@router.get("", response_model=MeResponse)
async def get_me(session: AsyncSessionDep, user: CurrentUser):
    base = AccountRole.AC if AccountRole.AC in user.roles else next(iter(user.roles), None)
    model = _PROFILE_MODEL.get(base)
    has_profile = model is None or await session.get(model, user.camwa_id) is not None
    claims = user.claims
    return MeResponse(
        camwa_id=user.camwa_id,
        email=claims.get("email"),
        first_name=claims.get("given_name"),
        last_name=claims.get("family_name"),
        phone_number=claims.get("phone_number"),
        roles=sorted(user.roles, key=lambda r: r.value),
        acting_role=user.acting,
        program_id=user.program_id,
        has_profile=has_profile,
    )


@router.put("/password", response_model=TokenResponse)
async def change_password(data: PasswordChange, user: AllAuthenticated):
    try:
        await keycloak.login(user.camwa_id, data.current_password)
    except HTTPException as exc:
        if exc.status_code == 401:
            raise HTTPException(status_code=403, detail="Current password is wrong")
        raise
    account = await keycloak.get_user(user.camwa_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    await keycloak.set_password(account.id, data.new_password)
    await keycloak.end_sessions(account.id)
    return TokenResponse.model_validate(await keycloak.login(user.camwa_id, data.new_password))


@router.put("/acting-role", response_model=ActingRole)
async def set_acting_role(session: AsyncSessionDep, data: ActingRole, user: CurrentUser):
    if AccountRole.AC not in user.roles:
        raise HTTPException(status_code=403, detail="Only academic coordinators have an acting role")
    coordinator = await session.get(AcademicCoordinator, user.camwa_id)
    if coordinator is None:
        raise HTTPException(status_code=403, detail="Your CAMWA profile is not set up yet. Ask your faculty office.")
    if coordinator.current_role != data.role:
        coordinator.current_role = data.role
        await session.commit()
    return ActingRole(role=coordinator.current_role)


@router.get("/registrations", response_model=Page[ModuleRegistrationResponse])
async def list_my_registrations(session: AsyncSessionDep, page: PageDep, user: StudentOnly):
    scope = ModuleRegistration.student_id == user.camwa_id
    return await module_registration_service.list_registrations(session, page, scope)


@router.get("/attendance-summary")
async def get_my_attendance_summary(session: AsyncSessionDep, user: StudentOnly):
    return await student_service.get_student_modules_with_attendance_rate(session, user.camwa_id)


@router.get("/exam-eligibility")
async def get_my_exam_eligibility(session: AsyncSessionDep, user: StudentOnly):
    return await student_service.get_student_exam_eligibility_status(session, user.camwa_id)


@router.get("/images")
async def list_my_images(session: AsyncSessionDep, user: StudentOnly):
    return await student_service.get_student_images(session, user.camwa_id)


@router.get("/modules")
async def list_my_modules(session: AsyncSessionDep, user: LecturerOrAC):
    return await module_registration_service.get_lecturer_modules_with_student_count(session, user.camwa_id)


@router.get("/modules/attendance", response_model=LecturerStudentsAttendanceResponse)
async def get_my_modules_attendance(session: AsyncSessionDep, user: LecturerOrAC, module_id: Optional[str] = None):
    return await module_registration_service.get_lecturer_students_with_attendance_rate(
        session, user.camwa_id, module_id
    )


@router.get("/notifications", response_model=Page[NotificationResponse])
async def list_my_notifications(
    session: AsyncSessionDep, page: PageDep, user: AllAuthenticated, status: Optional[NotificationStatus] = None
):
    return await notification_service.list_notifications(session, page, notification_scope(user), status)


@router.patch("/notifications", response_model=NotificationCount)
async def update_all_my_notifications(session: AsyncSessionDep, data: NotificationStatusUpdate, user: AllAuthenticated):
    count = await notification_service.update_all_status(session, notification_scope(user), data.status)
    return NotificationCount(count=count)


@router.get("/notifications/unread-count", response_model=NotificationCount)
async def count_my_unread_notifications(session: AsyncSessionDep, user: AllAuthenticated):
    return NotificationCount(count=await notification_service.count_unread(session, notification_scope(user)))


@router.patch("/notifications/{notification_id}", response_model=NotificationResponse)
async def update_my_notification(
    session: AsyncSessionDep, notification_id: int, data: NotificationStatusUpdate, user: AllAuthenticated
):
    row = await notification_service.find_notification(session, notification_id, notification_scope(user))
    return await notification_service.update_notification_status(session, row, data.status)


@router.delete("/notifications/{notification_id}", status_code=204)
async def delete_my_notification(session: AsyncSessionDep, notification_id: int, user: AllAuthenticated):
    row = await notification_service.find_notification(session, notification_id, notification_scope(user))
    await notification_service.delete_notification(session, row)
