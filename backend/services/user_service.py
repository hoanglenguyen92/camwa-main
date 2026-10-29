import csv
import io

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.keycloak import NewUser, UserAccount, UserExists, keycloak
from backend.models import AcademicCoordinator, FacilityFaculty, Intake, Lecturer, Program, Student
from backend.models.enums import AccountRole, CoordinatorRole
from backend.schemas.users import UserImportReport, UserImportRow, UserImportRowResult

MAX_IMPORT_ROWS = 2000
CSV_COLUMNS = ("camwa_id", "email", "first_name", "last_name", "role", "program_id", "intake", "phone_number")


def _bad_rows(errors: list[dict]) -> HTTPException:
    return HTTPException(status_code=422, detail={"message": "Invalid rows. Nothing was imported.", "rows": errors})


async def parse_import(session: AsyncSession, contents: bytes) -> list[tuple[int, UserImportRow]]:
    """Validates the whole file before anything is created. Row numbers count the header as row 1."""
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="The file must be UTF-8 CSV")
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in CSV_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {', '.join(missing)}")

    rows: list[tuple[int, UserImportRow]] = []
    errors: list[dict] = []
    for line, raw in enumerate(reader, start=2):
        if line - 1 > MAX_IMPORT_ROWS:
            raise HTTPException(status_code=413, detail=f"At most {MAX_IMPORT_ROWS} rows per file")
        try:
            rows.append((line, UserImportRow.model_validate({c: (raw.get(c) or "").strip() for c in CSV_COLUMNS})))
        except ValidationError as exc:
            errors.append({"row": line, "errors": [f"{'.'.join(map(str, e['loc'])) or 'row'}: {e['msg']}" for e in exc.errors()]})
    if not rows and not errors:
        raise HTTPException(status_code=400, detail="The file has no rows")

    programs = set(await session.scalars(select(Program.program_id)))
    intakes = set(await session.scalars(select(Intake.year)))
    seen_ids: dict[str, int] = {}
    seen_emails: dict[str, int] = {}
    for line, row in rows:
        problems = []
        if row.program_id not in programs:
            problems.append(f"program_id: {row.program_id} does not exist")
        if row.intake is not None and row.intake not in intakes:
            problems.append(f"intake: {row.intake} does not exist")
        if row.camwa_id in seen_ids:
            problems.append(f"camwa_id: duplicate of row {seen_ids[row.camwa_id]}")
        if row.email.lower() in seen_emails:
            problems.append(f"email: duplicate of row {seen_emails[row.email.lower()]}")
        seen_ids.setdefault(row.camwa_id, line)
        seen_emails.setdefault(row.email.lower(), line)
        if problems:
            errors.append({"row": line, "errors": problems})
    if errors:
        raise _bad_rows(sorted(errors, key=lambda e: e["row"]))
    return rows


def _profiles(row: UserImportRow) -> list:
    if row.role == AccountRole.STUDENT:
        return [Student(student_id=row.camwa_id, name=row.name, program_id=row.program_id, intake=row.intake)]
    if row.role == AccountRole.FA:
        return [FacilityFaculty(staff_id=row.camwa_id, name=row.name, program_id=row.program_id)]
    lecturer = Lecturer(lecturer_id=row.camwa_id, name=row.name, program_id=row.program_id)
    if row.role == AccountRole.LECTURER:
        return [lecturer]
    # An AC teaches too, and module.lecturer_id points at lecturer.
    coordinator = AcademicCoordinator(
        ac_id=row.camwa_id, name=row.name, program_id=row.program_id, current_role=CoordinatorRole.AC
    )
    return [lecturer, coordinator]


async def ensure_profiles(session: AsyncSession, row: UserImportRow) -> None:
    for profile in _profiles(row):
        key = inspect(type(profile)).primary_key_from_instance(profile)
        if await session.get(type(profile), tuple(key)) is None:
            session.add(profile)
    try:
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise


async def _import_row(session: AsyncSession, line: int, row: UserImportRow) -> UserImportRowResult:
    result = lambda outcome, reason=None: UserImportRowResult(row=line, camwa_id=row.camwa_id, outcome=outcome, reason=reason)
    existing = await keycloak.get_user(row.camwa_id)
    if existing is None:
        by_email = await keycloak.find_user_by_email(row.email)
        if by_email is not None:
            return result("failed", f"email belongs to account {by_email.camwa_id}")
        try:
            account = await keycloak.create_user(
                NewUser(
                    camwa_id=row.camwa_id,
                    email=row.email,
                    first_name=row.first_name,
                    last_name=row.last_name,
                    role=row.role.value,
                    phone_number=row.phone_number,
                )
            )
        except UserExists:
            return result("skipped", "account already exists")
    try:
        await ensure_profiles(session, row)
    except SQLAlchemyError as exc:
        return result("failed", f"profile not saved: {exc.__class__.__name__}")
    if existing is not None:
        return result("skipped", "account already exists")
    try:
        await keycloak.send_set_password_email(account.id)
    except HTTPException:
        return result("created", "set-password email not sent; use password reset")
    return result("created")


async def import_users(session: AsyncSession, contents: bytes) -> UserImportReport:
    rows = await parse_import(session, contents)
    results = []
    for line, row in rows:
        try:
            results.append(await _import_row(session, line, row))
        except HTTPException as exc:
            results.append(UserImportRowResult(row=line, camwa_id=row.camwa_id, outcome="failed", reason=str(exc.detail)))
    return UserImportReport(
        created=sum(r.outcome == "created" for r in results),
        skipped=sum(r.outcome == "skipped" for r in results),
        failed=sum(r.outcome == "failed" for r in results),
        rows=results,
    )


async def get_account(camwa_id: str) -> UserAccount:
    account = await keycloak.get_user(camwa_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


async def set_account_active(camwa_id: str, active: bool) -> UserAccount:
    account = await get_account(camwa_id)
    await keycloak.set_active(account.id, active)
    return await get_account(camwa_id)
