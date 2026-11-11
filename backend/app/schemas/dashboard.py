from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DashboardCounts(BaseModel):
    academic_years: int
    students: int
    faculty: int
    subjects: int
    labs: int
    students_face_registered: int
    students_face_not_registered: int


class YearDashboardSummary(BaseModel):
    academic_year_id: int
    name: str
    programme_name: str
    student_count: int
    subject_count: int
    timetable_entries_count: int
    expected_weekly_periods: int
    face_registered_count: int
    attendance_percentage: Optional[float] = None


class TodayDashboardSummary(BaseModel):
    date: str
    sessions_total: int
    sessions_open: int
    sessions_closed: int
    present_count: int
    absent_count: int


class RecentSessionSummary(BaseModel):
    id: int
    date: str
    status: str
    subject_name: str
    faculty_name: str
    academic_year_name: str
    programme_name: str
    present_count: int
    absent_count: int


class FacultyScheduleItem(BaseModel):
    id: int
    day: str
    period: str
    subject_name: str
    academic_year_name: str
    programme_name: str
    lab_name: Optional[str] = None


class FacultySessionSummary(BaseModel):
    id: int
    date: str
    subject_name: str
    academic_year_name: str
    programme_name: str
    status: str
    present_count: int
    absent_count: int


class FacultyDashboardResponse(BaseModel):
    faculty_name: str
    subject_count: int
    student_count: int
    today_sessions_total: int
    today_sessions_open: int
    today_sessions_closed: int
    today_present_count: int
    today_absent_count: int
    recent_sessions: list[FacultySessionSummary] = Field(default_factory=list)
    upcoming_classes: list[FacultyScheduleItem] = Field(default_factory=list)


class StudentAttendanceSummary(BaseModel):
    present_count: int
    absent_count: int
    total_count: int
    percentage: float


class StudentRecentSession(BaseModel):
    id: int
    date: str
    subject_name: str
    faculty_name: str
    status: str
    present: bool


class StudentScheduleItem(BaseModel):
    id: int
    day: str
    period: str
    subject_name: str
    faculty_name: str
    academic_year_name: str
    programme_name: str


class StudentDashboardResponse(BaseModel):
    student_name: str
    roll_number: str
    academic_year_name: str
    programme_name: str
    attendance: StudentAttendanceSummary
    subject_count: int
    class_count: int
    recent_sessions: list[StudentRecentSession] = Field(default_factory=list)
    upcoming_classes: list[StudentScheduleItem] = Field(default_factory=list)


class LowAttendanceStudent(BaseModel):
    student_id: int
    name: str
    roll_number: str
    academic_year_name: str
    programme_name: str
    percentage: float


class HODDashboardResponse(BaseModel):
    counts: DashboardCounts
    years: list[YearDashboardSummary]
    today: TodayDashboardSummary
    recent_sessions: list[RecentSessionSummary]
    low_attendance_students: list[LowAttendanceStudent]
    warnings: list[str] = Field(default_factory=list)
