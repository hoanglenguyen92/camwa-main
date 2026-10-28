from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

from backend.core.db import engine, init_db
from backend.controllers import auth, account, intake, semester, student, program, module, module_registration, \
    lecturer, facility_faculty, dashboard, notification, attendance


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


# register_exception_handlers(app)


api_prefix = "/api"
app.include_router(account.router, prefix=api_prefix)
app.include_router(auth.router, prefix=api_prefix)
app.include_router(intake.router, prefix=api_prefix)
app.include_router(semester.router, prefix=api_prefix)
app.include_router(student.router, prefix=api_prefix)
app.include_router(program.router, prefix=api_prefix)
app.include_router(module.router, prefix=api_prefix)
app.include_router(facility_faculty.router, prefix=api_prefix)
app.include_router(lecturer.router, prefix=api_prefix)
app.include_router(module_registration.router, prefix=api_prefix)
app.include_router(notification.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)
app.include_router(attendance.router, prefix=api_prefix)


@app.get("/api")
async def root():
    return {"message": "Welcome to the API"}