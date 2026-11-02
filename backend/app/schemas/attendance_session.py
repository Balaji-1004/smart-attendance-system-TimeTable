from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import SessionStatus


class AttendanceSessionCreate(BaseModel):
    timetable_entry_id: int


class AttendanceSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timetable_entry_id: int
    faculty_id: int
    subject_id: int
    academic_year_id: int
    date: date
    start_time: datetime
    end_time: Optional[datetime] = None
    status: SessionStatus
    absent_marked_count: Optional[int] = None
