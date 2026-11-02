from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AcademicYearCreate(BaseModel):
    department_id: int
    name: str = Field(..., min_length=1)


class AcademicYearResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    name: str
    created_at: datetime
