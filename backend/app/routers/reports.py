from collections import defaultdict
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.database import get_db
from app.models import Attendance, Student, Subject, User
from app.models.enums import AttendanceStatus
from app.schemas.reports import (
    AttendanceReportRow,
    ClassAttendanceSummary,
    StudentAttendanceSummary,
    SubjectAttendanceSummary,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _faculty_subject_ids(db: Session, current_user: User) -> Optional[set[int]]:
    if current_user.role.value == "HOD":
        return None
    return {
        subject_id
        for (subject_id,) in db.query(Subject.id)
        .filter(Subject.faculty_id == current_user.faculty_id)
        .all()
    }


def _row_response(row: Attendance) -> AttendanceReportRow:
    return AttendanceReportRow(
        id=row.id,
        attendance_session_id=row.attendance_session_id,
        student_id=row.student_id,
        student_name=row.student.name,
        subject_id=row.subject_id,
        subject_name=row.subject.name,
        faculty_id=row.faculty_id,
        academic_year_id=row.academic_year_id,
        date=row.date,
        time=row.time,
        status=row.status,
        timetable_entry_id=row.timetable_entry_id,
    )


@router.get("/attendance/daily", response_model=list[AttendanceReportRow])
def daily_attendance_report(
    date_value: date = Query(..., alias="date"),
    academic_year_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    query = db.query(Attendance).filter(Attendance.date == date_value)
    allowed_subjects = _faculty_subject_ids(db, current_user)
    if allowed_subjects is not None:
        if not allowed_subjects:
            return []
        query = query.filter(Attendance.subject_id.in_(allowed_subjects))
    if academic_year_id is not None:
        query = query.filter(Attendance.academic_year_id == academic_year_id)
    if subject_id is not None:
        query = query.filter(Attendance.subject_id == subject_id)
    return [_row_response(row) for row in query.order_by(Attendance.time.asc()).all()]


@router.get("/attendance/subject/{subject_id}", response_model=list[StudentAttendanceSummary])
def subject_attendance_report(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if subject is None:
        return []
    allowed_subjects = _faculty_subject_ids(db, current_user)
    if allowed_subjects is not None and subject_id not in allowed_subjects:
        return []

    counts_by_student = defaultdict(lambda: {"present": 0, "total": 0})
    for student_id, attendance_status in (
        db.query(Attendance.student_id, Attendance.status)
        .filter(
            Attendance.subject_id == subject_id,
            Attendance.academic_year_id == subject.academic_year_id,
        )
        .all()
    ):
        counts_by_student[student_id]["total"] += 1
        if attendance_status == AttendanceStatus.PRESENT:
            counts_by_student[student_id]["present"] += 1

    students = (
        db.query(Student)
        .filter(Student.academic_year_id == subject.academic_year_id)
        .order_by(Student.id.asc())
        .all()
    )
    return [
        StudentAttendanceSummary(
            student_id=student.id,
            student_name=student.name,
            present_count=counts_by_student[student.id]["present"],
            total_count=counts_by_student[student.id]["total"],
            percentage=(
                round(
                    counts_by_student[student.id]["present"]
                    / counts_by_student[student.id]["total"]
                    * 100,
                    2,
                )
                if counts_by_student[student.id]["total"]
                else 0
            ),
        )
        for student in students
    ]


@router.get("/attendance/student/{student_id}", response_model=list[AttendanceReportRow])
def student_attendance_history(
    student_id: int,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    query = db.query(Attendance).filter(Attendance.student_id == student_id)
    allowed_subjects = _faculty_subject_ids(db, current_user)
    if allowed_subjects is not None:
        if not allowed_subjects:
            return []
        query = query.filter(Attendance.subject_id.in_(allowed_subjects))
    if subject_id is not None:
        query = query.filter(Attendance.subject_id == subject_id)
    return [_row_response(row) for row in query.order_by(Attendance.date.asc(), Attendance.time.asc()).all()]


@router.get("/attendance/class-summary/{academic_year_id}", response_model=list[ClassAttendanceSummary])
def class_attendance_summary(
    academic_year_id: int,
    faculty_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    query = db.query(Subject).filter(Subject.academic_year_id == academic_year_id)
    if current_user.role.value == "FACULTY":
        query = query.filter(Subject.faculty_id == current_user.faculty_id)
    elif faculty_id is not None:
        query = query.filter(Subject.faculty_id == faculty_id)

    subjects = query.order_by(Subject.id.asc()).all()
    if not subjects:
        return []
    subject_ids = [subject.id for subject in subjects]
    rows = (
        db.query(Attendance)
        .filter(
            Attendance.academic_year_id == academic_year_id,
            Attendance.subject_id.in_(subject_ids),
        )
        .all()
    )
    counts = defaultdict(lambda: {"present": 0, "absent": 0})
    for row in rows:
        if row.status == AttendanceStatus.PRESENT:
            counts[row.subject_id]["present"] += 1
        elif row.status == AttendanceStatus.ABSENT:
            counts[row.subject_id]["absent"] += 1

    return [
        ClassAttendanceSummary(
            subject_id=subject.id,
            subject_name=subject.name,
            present_count=counts[subject.id]["present"],
            absent_count=counts[subject.id]["absent"],
            total_count=counts[subject.id]["present"] + counts[subject.id]["absent"],
            percentage=(
                round(
                    counts[subject.id]["present"]
                    / (counts[subject.id]["present"] + counts[subject.id]["absent"])
                    * 100,
                    2,
                )
                if counts[subject.id]["present"] + counts[subject.id]["absent"]
                else 0
            ),
        )
        for subject in subjects
    ]
