from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import AttendanceStatus


class AttendanceReportRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attendance_session_id: int
    student_id: int
    student_name: str
    subject_id: int
    subject_name: str
    faculty_id: int
    academic_year_id: int
    date: date
    time: datetime
    status: AttendanceStatus
    timetable_entry_id: int


class StudentAttendanceSummary(BaseModel):
    student_id: int
    student_name: str
    present_count: int
    total_count: int
    percentage: float


class SubjectAttendanceSummary(BaseModel):
    subject_id: int
    subject_name: str
    present_count: int
    absent_count: int
    total_count: int
    percentage: float


class ClassAttendanceSummary(BaseModel):
    subject_id: int
    subject_name: str
    present_count: int
    absent_count: int
    total_count: int
    percentage: float
