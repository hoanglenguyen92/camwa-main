from pydantic import BaseModel


class IntakeResponse(BaseModel):
    year: int
    model_config = {"from_attributes": True}


class IntakeCreate(BaseModel):
    year: int


class IntakeUpdate(BaseModel):
    year: int