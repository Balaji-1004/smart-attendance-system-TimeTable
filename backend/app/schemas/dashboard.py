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
    present_count: int
    absent_count: int


class LowAttendanceStudent(BaseModel):
    student_id: int
    name: str
    roll_number: str
    academic_year_name: str
    percentage: float


class HODDashboardResponse(BaseModel):
    counts: DashboardCounts
    years: list[YearDashboardSummary]
    today: TodayDashboardSummary
    recent_sessions: list[RecentSessionSummary]
    low_attendance_students: list[LowAttendanceStudent]
    warnings: list[str] = Field(default_factory=list)
