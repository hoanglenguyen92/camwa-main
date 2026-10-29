import asyncio
import os
import tempfile
from pathlib import Path

_DB = Path(tempfile.mkdtemp()) / "camwa-test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
os.environ["KEYCLOAK_URL"] = "http://keycloak.test"
os.environ["KEYCLOAK_CLIENT_SECRET"] = "test-secret"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.core.db import Base, get_async_session
from backend.core.keycloak import keycloak
from backend.models import (
    AcademicCoordinator,
    AttendanceRequest,
    Attendance,
    FacilityFaculty,
    Intake,
    Lecturer,
    Module,
    Notification,
    Program,
    Semester,
    Student,
)
from backend.models.enums import AttendanceStatus, CoordinatorRole, NotificationType
from main import app
from tests.fake_keycloak import FakeKeycloak

engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _session():
    async with Session() as session:
        yield session


app.dependency_overrides[get_async_session] = _session

# Two programs, so reach checks have something to exclude.
FIXTURES = [
    Program(program_id="CSE", name="Computer Science"),
    Program(program_id="EE", name="Electrical"),
    Intake(year=2021),
    Semester(sem_id="WS2025"),
    FacilityFaculty(staff_id="100", name="FA Cse", program_id="CSE"),
    FacilityFaculty(staff_id="101", name="FA Ee", program_id="EE"),
    Lecturer(lecturer_id="200", name="Lecturer Cse", program_id="CSE"),
    Lecturer(lecturer_id="201", name="Lecturer Ee", program_id="EE"),
    Lecturer(lecturer_id="300", name="Coordinator Cse", program_id="CSE"),
    AcademicCoordinator(ac_id="300", name="Coordinator Cse", program_id="CSE", current_role=CoordinatorRole.AC),
    Student(student_id="400", name="Student Cse", program_id="CSE", intake=2021),
    Student(student_id="401", name="Student Ee", program_id="EE", intake=2021),
    Module(module_id="M-CSE", name="Algorithms", lecturer_id="200", program_id="CSE", intake=2021, semester_id="WS2025"),
    Module(module_id="M-EE", name="Circuits", lecturer_id="201", program_id="EE", intake=2021, semester_id="WS2025"),
    Attendance(attendance_id=1, student_id="400", module_id="M-CSE", attendance_status=AttendanceStatus.ABSENT),
    Attendance(attendance_id=2, student_id="401", module_id="M-EE", attendance_status=AttendanceStatus.ABSENT),
    AttendanceRequest(request_id=1, attendance_id=1, student_id="400", module_id="M-CSE", proposed_status=AttendanceStatus.PRESENT),
    AttendanceRequest(request_id=2, attendance_id=2, student_id="401", module_id="M-EE", proposed_status=AttendanceStatus.PRESENT),
    Notification(notification_id=1, sender_id="400", receiver_id="FACULTY", notification_type=NotificationType.NEW_REQUEST, request_id=1),
    Notification(notification_id=2, sender_id="401", receiver_id="FACULTY", notification_type=NotificationType.NEW_REQUEST, request_id=2),
    Notification(notification_id=3, sender_id="100", receiver_id="400", notification_type=NotificationType.REQUEST_APPROVED, request_id=1),
]


async def _reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as session:
        for row in FIXTURES:
            session.add(row.__class__(**{c.key: getattr(row, c.key) for c in row.__table__.columns if getattr(row, c.key) is not None}))
            await session.flush()
        await session.commit()


@pytest.fixture
def kc():
    fake = FakeKeycloak()
    keycloak.transport = fake.transport
    keycloak._http = None
    keycloak._keys = {}
    keycloak._keys_fetched_at = 0.0
    keycloak._admin_token = None
    return fake


@pytest.fixture
def client(kc):
    asyncio.run(_reset_db())
    with TestClient(app, base_url="http://test/api/v1") as c:
        yield c


@pytest.fixture
def as_user(kc):
    def headers(username: str, *roles: str) -> dict:
        return {"Authorization": f"Bearer {kc.token(username, *roles)}"}
    return headers


@pytest.fixture
def db():
    def run(coro_fn):
        async def go():
            async with Session() as session:
                return await coro_fn(session)
        return asyncio.run(go())
    return run
