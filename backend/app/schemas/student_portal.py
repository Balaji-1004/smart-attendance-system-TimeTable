from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import AttendanceStatus


class StudentProfileResponse(BaseModel):
    name: str
    roll_number: str
    email: str
    academic_year_name: str
    programme_name: str
    department_name: str
    face_registered: bool


class StudentSubjectAttendanceSummary(BaseModel):
    subject_id: int
    subject_name: str
    present_count: int
    absent_count: int
    total_count: int
    percentage: float


class StudentAttendanceSummaryResponse(BaseModel):
    subjects: list[StudentSubjectAttendanceSummary]
    overall_percentage: float


class StudentAttendanceHistoryResponse(BaseModel):
    date: date
    time: datetime
    subject_name: str
    status: AttendanceStatus
