from __future__ import annotations

from datetime import date

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models import AcademicYear, Attendance, AttendanceSession, Faculty, Lab, Student, Subject, TimetableEntry
from app.models.enums import AttendanceStatus, SessionStatus


def _safe_percentage(present: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round((present / total) * 100, 2)


def _build_warnings(year_summaries: list[dict], students_without_face: list[dict]) -> list[str]:
    warnings: list[str] = []

    for year in year_summaries:
        if year["student_count"] == 0:
            warnings.append(f"Academic year '{year['name']}' has no students.")
        if year["timetable_entries_count"] == 0:
            warnings.append(f"Academic year '{year['name']}' has no timetable entries.")
        if year["expected_weekly_periods"] > 0 and year["timetable_entries_count"] < year["expected_weekly_periods"]:
            warnings.append(
                f"Academic year '{year['name']}' has {year['timetable_entries_count']} timetable entries against {year['expected_weekly_periods']} expected weekly periods."
            )

    for student in students_without_face:
        warnings.append(f"Student '{student['name']}' ({student['roll_number']}) has no registered face.")

    return warnings


def get_hod_dashboard(db: Session, department_id: int) -> dict:
    today_value = date.today()

    counts = {
        "academic_years": db.query(AcademicYear).filter(AcademicYear.department_id == department_id).count(),
        "students": db.query(Student).filter(Student.department_id == department_id).count(),
        "faculty": db.query(Faculty).filter(Faculty.department_id == department_id).count(),
        "subjects": db.query(Subject)
        .join(AcademicYear, AcademicYear.id == Subject.academic_year_id)
        .filter(AcademicYear.department_id == department_id)
        .count(),
        "labs": db.query(Lab).filter(Lab.department_id == department_id).count(),
        "students_face_registered": db.query(Student)
        .filter(Student.department_id == department_id, Student.face_registered.is_(True))
        .count(),
        "students_face_not_registered": db.query(Student)
        .filter(Student.department_id == department_id, Student.face_registered.is_(False))
        .count(),
    }

    student_count = (
        db.query(func.count(Student.id))
        .filter(Student.academic_year_id == AcademicYear.id)
        .correlate(AcademicYear)
        .scalar_subquery()
    )
    subject_count = (
        db.query(func.count(Subject.id))
        .filter(Subject.academic_year_id == AcademicYear.id)
        .correlate(AcademicYear)
        .scalar_subquery()
    )
    timetable_entries_count = (
        db.query(func.count(TimetableEntry.id))
        .filter(TimetableEntry.academic_year_id == AcademicYear.id)
        .correlate(AcademicYear)
        .scalar_subquery()
    )
    expected_weekly_periods = (
        db.query(func.coalesce(func.sum(Subject.weekly_periods), 0))
        .filter(Subject.academic_year_id == AcademicYear.id)
        .correlate(AcademicYear)
        .scalar_subquery()
    )
    face_registered_count = (
        db.query(func.count(Student.id))
        .filter(
            Student.academic_year_id == AcademicYear.id,
            Student.face_registered.is_(True),
        )
        .correlate(AcademicYear)
        .scalar_subquery()
    )
    year_rows = (
        db.query(
            AcademicYear.id.label("academic_year_id"),
            AcademicYear.name.label("name"),
            student_count.label("student_count"),
            subject_count.label("subject_count"),
            timetable_entries_count.label("timetable_entries_count"),
            expected_weekly_periods.label("expected_weekly_periods"),
            face_registered_count.label("face_registered_count"),
        )
        .filter(AcademicYear.department_id == department_id)
        .order_by(AcademicYear.id.asc())
        .all()
    )

    attendance_by_year = (
        db.query(
            Attendance.academic_year_id.label("academic_year_id"),
            func.sum(case((Attendance.status == AttendanceStatus.PRESENT, 1), else_=0)).label("present_count"),
            func.sum(case((Attendance.status == AttendanceStatus.ABSENT, 1), else_=0)).label("absent_count"),
        )
        .join(AcademicYear, AcademicYear.id == Attendance.academic_year_id)
        .filter(AcademicYear.department_id == department_id)
        .group_by(Attendance.academic_year_id)
        .all()
    )
    attendance_map = {
        row.academic_year_id: {
            "present_count": int(row.present_count or 0),
            "absent_count": int(row.absent_count or 0),
        }
        for row in attendance_by_year
    }

    year_summaries: list[dict] = []
    for row in year_rows:
        summary = {
            "academic_year_id": row.academic_year_id,
            "name": row.name,
            "student_count": int(row.student_count or 0),
            "subject_count": int(row.subject_count or 0),
            "timetable_entries_count": int(row.timetable_entries_count or 0),
            "expected_weekly_periods": int(row.expected_weekly_periods or 0),
            "face_registered_count": int(row.face_registered_count or 0),
        }
        attendance_stats = attendance_map.get(row.academic_year_id, {"present_count": 0, "absent_count": 0})
        total = attendance_stats["present_count"] + attendance_stats["absent_count"]
        summary["attendance_percentage"] = _safe_percentage(attendance_stats["present_count"], total)
        year_summaries.append(summary)

    today_counts = (
        db.query(
            func.count(AttendanceSession.id).label("sessions_total"),
            func.sum(case((AttendanceSession.status == SessionStatus.OPEN, 1), else_=0)).label("sessions_open"),
            func.sum(case((AttendanceSession.status == SessionStatus.CLOSED, 1), else_=0)).label("sessions_closed"),
        )
        .join(AcademicYear, AcademicYear.id == AttendanceSession.academic_year_id)
        .filter(AttendanceSession.date == today_value)
        .filter(AcademicYear.department_id == department_id)
        .one()
    )
    today_summary = {
        "date": today_value.isoformat(),
        "sessions_total": int(today_counts.sessions_total or 0),
        "sessions_open": int(today_counts.sessions_open or 0),
        "sessions_closed": int(today_counts.sessions_closed or 0),
    }

    todays_attendance = (
        db.query(
            func.sum(case((Attendance.status == AttendanceStatus.PRESENT, 1), else_=0)).label("present_count"),
            func.sum(case((Attendance.status == AttendanceStatus.ABSENT, 1), else_=0)).label("absent_count"),
        )
        .join(AcademicYear, AcademicYear.id == Attendance.academic_year_id)
        .filter(Attendance.date == today_value)
        .filter(AcademicYear.department_id == department_id)
        .one()
    )
    today_summary["present_count"] = int(todays_attendance.present_count or 0)
    today_summary["absent_count"] = int(todays_attendance.absent_count or 0)

    recent_sessions = (
        db.query(
            AttendanceSession.id,
            AttendanceSession.date,
            AttendanceSession.status,
            Subject.name.label("subject_name"),
            Faculty.name.label("faculty_name"),
            AcademicYear.name.label("academic_year_name"),
        )
        .join(Subject, Subject.id == AttendanceSession.subject_id)
        .join(Faculty, Faculty.id == AttendanceSession.faculty_id)
        .join(AcademicYear, AcademicYear.id == AttendanceSession.academic_year_id)
        .filter(AcademicYear.department_id == department_id)
        .order_by(AttendanceSession.date.desc(), AttendanceSession.id.desc())
        .limit(5)
        .all()
    )
    session_counts = (
        db.query(
            Attendance.attendance_session_id.label("attendance_session_id"),
            func.sum(case((Attendance.status == AttendanceStatus.PRESENT, 1), else_=0)).label("present_count"),
            func.sum(case((Attendance.status == AttendanceStatus.ABSENT, 1), else_=0)).label("absent_count"),
        )
        .join(AcademicYear, AcademicYear.id == Attendance.academic_year_id)
        .filter(AcademicYear.department_id == department_id)
        .group_by(Attendance.attendance_session_id)
        .all()
    )
    session_count_map = {
        row.attendance_session_id: {
            "present_count": int(row.present_count or 0),
            "absent_count": int(row.absent_count or 0),
        }
        for row in session_counts
    }
    recent_session_rows = []
    for row in recent_sessions:
        counts_for_session = session_count_map.get(row.id, {"present_count": 0, "absent_count": 0})
        recent_session_rows.append({
            "id": row.id,
            "date": row.date.isoformat(),
            "status": row.status.value if hasattr(row.status, "value") else str(row.status),
            "subject_name": row.subject_name,
            "faculty_name": row.faculty_name,
            "academic_year_name": row.academic_year_name,
            "present_count": counts_for_session["present_count"],
            "absent_count": counts_for_session["absent_count"],
        })

    low_attendance_rows = (
        db.query(
            Student.id.label("student_id"),
            Student.name,
            Student.roll_number,
            AcademicYear.name.label("academic_year_name"),
            func.sum(case((Attendance.status == AttendanceStatus.PRESENT, 1), else_=0)).label("present_count"),
            func.sum(case((Attendance.status == AttendanceStatus.ABSENT, 1), else_=0)).label("absent_count"),
            func.count(Attendance.id).label("attendance_total"),
        )
        .join(AcademicYear, AcademicYear.id == Student.academic_year_id)
        .outerjoin(Attendance, Attendance.student_id == Student.id)
        .filter(Student.department_id == department_id)
        .group_by(Student.id, Student.name, Student.roll_number, AcademicYear.name)
        .having(func.count(Attendance.id) > 0)
        .all()
    )

    low_attendance_students = []
    for row in low_attendance_rows:
        total = int(row.present_count or 0) + int(row.absent_count or 0)
        if total <= 0:
            continue
        percentage = _safe_percentage(int(row.present_count or 0), total) or 0.0
        if percentage < 75.0:
            low_attendance_students.append(
                {
                    "student_id": row.student_id,
                    "name": row.name,
                    "roll_number": row.roll_number,
                    "academic_year_name": row.academic_year_name,
                    "percentage": percentage,
                }
            )
    low_attendance_students = sorted(low_attendance_students, key=lambda item: (item["percentage"], item["student_id"]))[:10]

    students_without_face = (
        db.query(Student.id, Student.name, Student.roll_number)
        .filter(Student.department_id == department_id, Student.face_registered.is_(False))
        .order_by(Student.id.asc())
        .all()
    )

    warnings = _build_warnings(year_summaries, [
        {"name": row.name, "roll_number": row.roll_number} for row in students_without_face
    ])

    return {
        "counts": counts,
        "years": [
            {
                "academic_year_id": row["academic_year_id"],
                "name": row["name"],
                "student_count": row["student_count"],
                "subject_count": row["subject_count"],
                "timetable_entries_count": row["timetable_entries_count"],
                "expected_weekly_periods": row["expected_weekly_periods"],
                "face_registered_count": row["face_registered_count"],
                "attendance_percentage": row["attendance_percentage"],
            }
            for row in year_summaries
        ],
        "today": today_summary,
        "recent_sessions": recent_session_rows,
        "low_attendance_students": [
            {
                "student_id": row["student_id"],
                "name": row["name"],
                "roll_number": row["roll_number"],
                "academic_year_name": row["academic_year_name"],
                "percentage": row["percentage"],
            }
            for row in low_attendance_students
        ],
        "warnings": warnings,
    }
