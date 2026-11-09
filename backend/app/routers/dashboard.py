from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.security import get_user_department_id, require_role
from app.database.database import get_db
from app.models import Attendance, AttendanceSession, Faculty, Student, Subject, TimetableEntry, User
from app.models.enums import AttendanceStatus, SessionStatus
from app.schemas.dashboard import (
    FacultyDashboardResponse,
    HODDashboardResponse,
    StudentDashboardResponse,
)
from app.services.dashboard_service import get_hod_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/hod", response_model=HODDashboardResponse)
def get_hod_dashboard_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    return get_hod_dashboard(db, department_id)


@router.get("/faculty", response_model=FacultyDashboardResponse)
def get_faculty_dashboard_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("FACULTY")),
):
    faculty = db.query(Faculty).filter(Faculty.id == current_user.faculty_id).first()
    if faculty is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty profile not found")

    faculty_subject_ids = [row.id for row in db.query(Subject.id).filter(Subject.faculty_id == faculty.id).all()]
    student_count = 0
    if faculty_subject_ids:
        academic_year_ids = (
            db.query(Subject.academic_year_id)
            .filter(Subject.id.in_(faculty_subject_ids))
            .distinct()
            .subquery()
        )
        student_count = db.query(Student.id).filter(Student.academic_year_id.in_(academic_year_ids)).count()

    today = date.today()
    today_sessions = (
        db.query(AttendanceSession)
        .filter(AttendanceSession.faculty_id == faculty.id, AttendanceSession.date == today)
        .order_by(AttendanceSession.id.desc())
        .all()
    )

    recent_sessions = []
    for session in today_sessions[:5]:
        counts = (
            db.query(
                func.sum(case((Attendance.status == AttendanceStatus.PRESENT, 1), else_=0)).label("present_count"),
                func.sum(case((Attendance.status == AttendanceStatus.ABSENT, 1), else_=0)).label("absent_count"),
            )
            .filter(Attendance.attendance_session_id == session.id)
            .one()
        )
        recent_sessions.append({
            "id": session.id,
            "date": session.date.isoformat(),
            "subject_name": session.subject.name,
            "academic_year_name": session.academic_year.name,
            "status": session.status.value,
            "present_count": int(counts.present_count or 0),
            "absent_count": int(counts.absent_count or 0),
        })

    upcoming_classes = []
    for entry in (
        db.query(TimetableEntry)
        .filter(TimetableEntry.faculty_id == faculty.id)
        .order_by(TimetableEntry.day, TimetableEntry.period)
        .limit(10)
        .all()
    ):
        upcoming_classes.append({
            "id": entry.id,
            "day": entry.day.value,
            "period": entry.period.value,
            "subject_name": entry.subject.name,
            "academic_year_name": entry.academic_year.name,
            "lab_name": entry.lab.name if entry.lab else None,
        })

    today_present_count = (
        db.query(func.count(Attendance.id))
        .filter(Attendance.faculty_id == faculty.id, Attendance.date == today, Attendance.status == AttendanceStatus.PRESENT)
        .scalar()
        or 0
    )
    today_absent_count = (
        db.query(func.count(Attendance.id))
        .filter(Attendance.faculty_id == faculty.id, Attendance.date == today, Attendance.status == AttendanceStatus.ABSENT)
        .scalar()
        or 0
    )

    return {
        "faculty_name": faculty.name,
        "subject_count": len(faculty_subject_ids),
        "student_count": student_count,
        "today_sessions_total": len(today_sessions),
        "today_sessions_open": sum(1 for session in today_sessions if session.status == SessionStatus.OPEN),
        "today_sessions_closed": sum(1 for session in today_sessions if session.status == SessionStatus.CLOSED),
        "today_present_count": int(today_present_count),
        "today_absent_count": int(today_absent_count),
        "recent_sessions": recent_sessions,
        "upcoming_classes": upcoming_classes,
    }


@router.get("/student", response_model=StudentDashboardResponse)
def get_student_dashboard_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("STUDENT")),
):
    student = db.query(Student).filter(Student.id == current_user.student_id).first()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

    attendance_rows = (
        db.query(Attendance)
        .filter(Attendance.student_id == student.id)
        .order_by(Attendance.date.desc(), Attendance.id.desc())
        .all()
    )
    present_count = sum(1 for row in attendance_rows if row.status == AttendanceStatus.PRESENT)
    absent_count = sum(1 for row in attendance_rows if row.status == AttendanceStatus.ABSENT)
    total_count = present_count + absent_count
    percentage = round((present_count / total_count) * 100, 2) if total_count else 0.0

    recent_sessions = []
    for row in attendance_rows[:5]:
        recent_sessions.append({
            "id": row.id,
            "date": row.date.isoformat(),
            "subject_name": row.subject.name,
            "faculty_name": row.faculty.name,
            "status": "PRESENT" if row.status == AttendanceStatus.PRESENT else "ABSENT",
            "present": row.status == AttendanceStatus.PRESENT,
        })

    upcoming_classes = []
    for entry in (
        db.query(TimetableEntry)
        .filter(TimetableEntry.academic_year_id == student.academic_year_id)
        .order_by(TimetableEntry.day, TimetableEntry.period)
        .limit(10)
        .all()
    ):
        upcoming_classes.append({
            "id": entry.id,
            "day": entry.day.value,
            "period": entry.period.value,
            "subject_name": entry.subject.name,
            "faculty_name": entry.faculty.name,
            "academic_year_name": student.academic_year.name,
        })

    return {
        "student_name": student.name,
        "roll_number": student.roll_number,
        "academic_year_name": student.academic_year.name,
        "attendance": {
            "present_count": present_count,
            "absent_count": absent_count,
            "total_count": total_count,
            "percentage": percentage,
        },
        "subject_count": db.query(Subject).filter(Subject.academic_year_id == student.academic_year_id).count(),
        "class_count": db.query(TimetableEntry).filter(TimetableEntry.academic_year_id == student.academic_year_id).count(),
        "recent_sessions": recent_sessions,
        "upcoming_classes": upcoming_classes,
    }
