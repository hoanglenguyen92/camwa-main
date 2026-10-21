from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.core.db import AsyncSessionDep
from backend.core.deps import AdminOrFA, AdminOnly
from backend.helpers.response_wrapper import ApiResponse
from backend.schemas.module import ModuleResponse, ModuleCreate, ModuleUpdate, CameraPathUpdate
from backend.services import module_service

router = APIRouter(
    prefix="/module",
    tags=["Module"],
)


@router.post("/create", response_model=ApiResponse[ModuleResponse], status_code=201)
async def create_module(
        session: AsyncSessionDep,
        data: ModuleCreate,
        _: AdminOrFA = None
):
    module = await module_service.create_module(session, data)
    return ApiResponse(
        message="Module created successfully",
        meta_data=module
    )


@router.post("/delete-from-excel", response_model=ApiResponse)
async def delete_modules_from_excel(
    session: AsyncSessionDep,
    file: UploadFile = File(...),
    _: AdminOnly = None
):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .xlsx files are allowed.")
    contents = await file.read()
    result = await module_service.delete_multiple_modules_from_excel(session, contents)
    return ApiResponse(
        message="Modules deleted from Excel successfully",
        meta_data=result,
    )


@router.post("/create-from-excel", response_model=ApiResponse)
async def import_module(
        session: AsyncSessionDep,
        file: UploadFile = File(...),
        _: AdminOrFA = None
):
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in [".xlsx", ".xls"]):
        raise HTTPException(status_code=400, detail="Invalid file type. Only Excel files are allowed.")

    contents = await file.read()
    result = await module_service.create_multiple_module_from_excel(session, contents)
    return ApiResponse(
        message="Modules imported successfully",
        meta_data=result
    )



@router.get("/view", response_model=ApiResponse[List[ModuleResponse]])
async def view_modules(
        session: AsyncSessionDep,
        _: AdminOrFA = None
):
    modules = await module_service.view_modules(session)
    return ApiResponse(
        message="Modules retrieved successfully",
        meta_data=modules
    )


@router.get("/camera-path/{module_id}", response_model=ApiResponse[dict])
async def get_camera_path(
        module_id: str,
        session: AsyncSessionDep,
        _: AdminOnly = None
):
    result = await module_service.get_camera_path(session, module_id)
    return ApiResponse(
        message="Camera path retrieved successfully",
        meta_data=result
    )


@router.put("/set-camera-path/{module_id}", response_model=ApiResponse[dict])
async def set_camera_path(
    module_id: str,
    data: CameraPathUpdate,
    session: AsyncSessionDep,
    _: AdminOnly = None
):
    result = await module_service.set_camera_path(session, module_id, data.camera_path)
    return ApiResponse(
        message="Camera path set successfully",
        meta_data=result
    )

@router.put("/update/{module_id}", response_model=ApiResponse[ModuleResponse])
async def update_module(
        session: AsyncSessionDep,
        module_id: str,
        data: ModuleUpdate,
        _: AdminOnly = None
):
    module = await module_service.update_module(session, module_id, data)
    return ApiResponse(
        message="Module updated successfully",
        meta_data=module
    )


@router.delete("/delete/{module_id}", response_model=ApiResponse[None])
async def delete_module(
        session: AsyncSessionDep,
        module_id: str,
        _: AdminOnly = None
):
    await module_service.delete_module(session, module_id)
    return ApiResponse(
        message="Module deleted successfully",
        meta_data=None
    )