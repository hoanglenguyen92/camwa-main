from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

from backend.core.db import engine, init_db
from backend.controllers import (
    attendance,
    attendance_request,
    auth,
    dashboard,
    exam_eligibility,
    facility_faculty,
    intake,
    lecturer,
    me,
    module,
    module_registration,
    program,
    semester,
    student,
    users,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield
    await engine.dispose()

def operation_id(route: APIRoute) -> str:
    # "<Tag>.<handler>" becomes <Tag>Controller.<handler>() in the generated TypeScript client.
    tag = route.tags[0].replace(" ", "") if route.tags else "Api"
    return f"{tag}.{route.name}"


app = FastAPI(
    title="CAMWA FastAPI Backend",
    lifespan=lifespan,
    generate_unique_id_function=operation_id,
)


API_PREFIX = "/api/v1"
ROUTERS = (
    auth,
    me,
    users,
    intake,
    semester,
    program,
    facility_faculty,
    student,
    lecturer,
    module,
    module_registration,
    attendance,
    attendance_request,
    exam_eligibility,
    dashboard,
)
for controller in ROUTERS:
    app.include_router(controller.router, prefix=API_PREFIX)


@app.get(API_PREFIX)
async def root():
    return {"message": "Welcome to the API"}
