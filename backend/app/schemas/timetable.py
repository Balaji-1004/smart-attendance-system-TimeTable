from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Period, WeekDay


class TimetableGenerateRequest(BaseModel):
    academic_year_id: int


class TimetableGenerateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feasibility_warnings: dict
    placed_count: int
    unscheduled: list


class TimetableEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year_id: int
    subject_id: int
    subject_name: str
    faculty_id: int
    faculty_name: str
    day: WeekDay
    period: Period
    lab_id: Optional[int] = None
    lab_name: Optional[str] = None


class TimetableEntryUpdate(BaseModel):
    day: Optional[WeekDay] = None
    period: Optional[Period] = None
    lab_id: Optional[int] = None


class DepartmentTimetableEntryResponse(TimetableEntryResponse):
    academic_year_name: str
