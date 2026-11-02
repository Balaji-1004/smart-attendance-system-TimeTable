from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SubjectType


class SubjectCreate(BaseModel):
    academic_year_id: int
    name: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)
    subject_type: SubjectType
    weekly_periods: int = Field(..., gt=0)
    faculty_id: int


class SubjectUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    subject_type: SubjectType | None = None
    weekly_periods: int | None = Field(default=None, gt=0)
    faculty_id: int | None = None


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year_id: int
    name: str
    code: str
    subject_type: SubjectType
    weekly_periods: int
    faculty_id: int
    created_at: datetime
