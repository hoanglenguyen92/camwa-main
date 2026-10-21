from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.core.db import engine, init_db
from backend.routes import auth, account, intake, semester, student, program, module, module_registration, \
    lecturer, facility_faculty, dashboard, notification, attendance


app = FastAPI()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield
    await engine.dispose()

app = FastAPI(
    title="CAMWA FastAPI Backend",
    lifespan=lifespan,
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