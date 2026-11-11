from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AcademicYearCreate(BaseModel):
    programme_id: int
    name: str = Field(..., min_length=1)


class AcademicYearResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    programme_id: int
    programme_name: str
    name: str
    created_at: datetime
