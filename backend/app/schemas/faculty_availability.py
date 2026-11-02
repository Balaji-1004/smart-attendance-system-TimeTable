from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Period, WeekDay


class FacultyAvailabilityCreate(BaseModel):
    faculty_id: int
    day: WeekDay
    period: Period


class FacultyAvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    faculty_id: int
    day: WeekDay
    period: Period
