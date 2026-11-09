from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LabCreate(BaseModel):
    lab_code: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)


class LabUpdate(BaseModel):
    lab_code: str | None = None
    name: str | None = None


class LabResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int | None = None
    lab_code: str
    name: str
