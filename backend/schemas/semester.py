from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel


class SemesterResponse(BaseModel):
    sem_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    model_config = {"from_attributes": True}


class SemesterCreate(BaseModel):
    sem_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class SemesterUpdate(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None