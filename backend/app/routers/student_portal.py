from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.database import get_db
from app.models import User
from app.routers.timetable import _entry_to_response
from app.schemas.student_portal import (
    StudentAttendanceHistoryResponse,
    StudentAttendanceSummaryResponse,
    StudentProfileResponse,
)
from app.schemas.timetable import TimetableEntryResponse
from app.services.student_portal_service import (
    get_student_attendance_history,
    get_student_attendance_summary,
    get_student_for_user,
    get_student_profile,
    get_student_timetable,
)

router = APIRouter(prefix="/me", tags=["student-portal"])


@router.get("/profile", response_model=StudentProfileResponse)
def student_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("STUDENT")),
):
    student = get_student_for_user(db, current_user)
    return get_student_profile(student)


@router.get("/timetable", response_model=list[TimetableEntryResponse])
def student_timetable(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("STUDENT")),
):
    student = get_student_for_user(db, current_user)
    return [_entry_to_response(entry) for entry in get_student_timetable(db, student)]


@router.get("/attendance/summary", response_model=StudentAttendanceSummaryResponse)
def student_attendance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("STUDENT")),
):
    student = get_student_for_user(db, current_user)
    return get_student_attendance_summary(db, student)


@router.get("/attendance/history", response_model=list[StudentAttendanceHistoryResponse])
def student_attendance_history(
    subject_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("STUDENT")),
):
    student = get_student_for_user(db, current_user)
    return get_student_attendance_history(db, student, subject_id)
