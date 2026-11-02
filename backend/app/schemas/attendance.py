from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AttendanceStatus


class MarkAttendanceRequest(BaseModel):
    student_id: int


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attendance_session_id: int
    student_id: int
    subject_id: int
    faculty_id: int
    academic_year_id: int
    date: date
    time: datetime
    status: AttendanceStatus
    timetable_entry_id: int
