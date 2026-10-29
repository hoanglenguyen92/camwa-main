"""Row reach per acting role: ADMIN all, FA and AC own program, LECTURER own modules, STUDENT self.

Rows outside the caller's reach answer 404, so their existence isn't revealed.
"""
from typing import Optional, TypeVar

from fastapi import HTTPException
from sqlalchemy import ColumnElement, and_, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.deps import Principal
from backend.models import AttendanceRequest, Module, ModuleRegistration, Notification, Student
from backend.models.enums import AccountRole

T = TypeVar("T")

_PROGRAM_ROLES = (AccountRole.FA, AccountRole.AC)
FACULTY_INBOX = "FACULTY"


def module_scope(p: Principal, module_col) -> ColumnElement[bool]:
    if p.acting == AccountRole.ADMIN:
        return true()
    if p.acting in _PROGRAM_ROLES:
        return module_col.in_(select(Module.module_id).where(Module.program_id == p.program_id))
    if p.acting == AccountRole.LECTURER:
        return module_col.in_(select(Module.module_id).where(Module.lecturer_id == p.camwa_id))
    return module_col.in_(select(ModuleRegistration.module_id).where(ModuleRegistration.student_id == p.camwa_id))


def student_scope(p: Principal, student_col) -> ColumnElement[bool]:
    if p.acting == AccountRole.ADMIN:
        return true()
    if p.acting in _PROGRAM_ROLES:
        return student_col.in_(select(Student.student_id).where(Student.program_id == p.program_id))
    if p.acting == AccountRole.LECTURER:
        return student_col.in_(
            select(ModuleRegistration.student_id)
            .join(Module, Module.module_id == ModuleRegistration.module_id)
            .where(Module.lecturer_id == p.camwa_id)
        )
    return student_col == p.camwa_id


def row_scope(p: Principal, module_col, student_col) -> ColumnElement[bool]:
    """Rows that belong to a student in a module: registrations, attendance, requests, exams."""
    if p.acting == AccountRole.STUDENT:
        return student_col == p.camwa_id
    return module_scope(p, module_col)


def notification_scope(p: Principal) -> ColumnElement[bool]:
    """Own notifications, plus the shared FACULTY inbox for ADMIN and for FA within their program."""
    own = Notification.receiver_id == p.camwa_id
    if p.acting == AccountRole.ADMIN:
        return or_(own, Notification.receiver_id == FACULTY_INBOX)
    if p.acting == AccountRole.FA:
        in_program = Notification.request_id.in_(
            select(AttendanceRequest.request_id)
            .join(Module, Module.module_id == AttendanceRequest.module_id)
            .where(Module.program_id == p.program_id)
        )
        return or_(own, and_(Notification.receiver_id == FACULTY_INBOX, in_program))
    return own


async def _one_in_reach(session: AsyncSession, model: type[T], key_col, key, scope, detail: str) -> T:
    row = await session.scalar(select(model).where(key_col == key, scope))
    if row is None:
        raise HTTPException(status_code=404, detail=detail)
    return row


async def ensure_student_access(p: Principal, session: AsyncSession, student_id: str) -> Student:
    return await _one_in_reach(
        session, Student, Student.student_id, student_id, student_scope(p, Student.student_id), "Student not found"
    )


async def ensure_module_access(p: Principal, session: AsyncSession, module_id: str) -> Module:
    return await _one_in_reach(
        session, Module, Module.module_id, module_id, module_scope(p, Module.module_id), "Module not found"
    )


async def ensure_row_access(p: Principal, session: AsyncSession, model: type[T], key_col, key, detail: str) -> T:
    return await _one_in_reach(session, model, key_col, key, row_scope(p, model.module_id, model.student_id), detail)


def ensure_program_write(p: Principal, program_id: Optional[str]) -> None:
    """FA writes stay inside their own program. ADMIN writes anywhere."""
    if p.acting != AccountRole.ADMIN and program_id != p.program_id:
        raise HTTPException(status_code=403, detail="Outside your program")
