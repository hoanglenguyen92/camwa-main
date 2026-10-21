from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    status: str = "success"
    code: int = 200
    message: str = ""
    meta_data: Optional[T] = None