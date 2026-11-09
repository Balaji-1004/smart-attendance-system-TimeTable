from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Attendance, Student, Subject, TimetableEntry, User
from app.models.enums import AttendanceStatus


def get_student_for_user(db: Session, user: User) -> Student:
    if user.student_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    student = db.query(Student).filter(Student.id == user.student_id).first()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    return student


def get_student_profile(student: Student) -> dict:
    return {
        "name": student.name,
        "roll_number": student.roll_number,
        "email": student.email,
        "academic_year_name": student.academic_year.name,
        "department_name": student.department.name,
        "face_registered": student.face_registered,
    }


def get_student_timetable(db: Session, student: Student):
    return (
        db.query(TimetableEntry)
        .filter(TimetableEntry.academic_year_id == student.academic_year_id)
        .order_by(TimetableEntry.day, TimetableEntry.period, TimetableEntry.id)
        .all()
    )


def get_student_attendance_summary(db: Session, student: Student) -> dict:
    counts_by_subject = defaultdict(lambda: {"present": 0, "absent": 0})
    attendance_counts = (
        db.query(Attendance.subject_id, Attendance.status)
        .filter(
            Attendance.student_id == student.id,
            Attendance.academic_year_id == student.academic_year_id,
        )
        .all()
    )
    for subject_id, attendance_status in attendance_counts:
        if attendance_status == AttendanceStatus.PRESENT:
            counts_by_subject[subject_id]["present"] += 1
        elif attendance_status == AttendanceStatus.ABSENT:
            counts_by_subject[subject_id]["absent"] += 1

    subjects = (
        db.query(Subject)
        .filter(Subject.academic_year_id == student.academic_year_id)
        .order_by(Subject.id)
        .all()
    )
    summary = []
    total_present = 0
    total_absent = 0
    for subject in subjects:
        present = counts_by_subject[subject.id]["present"]
        absent = counts_by_subject[subject.id]["absent"]
        total = present + absent
        total_present += present
        total_absent += absent
        summary.append(
            {
                "subject_id": subject.id,
                "subject_name": subject.name,
                "present_count": present,
                "absent_count": absent,
                "total_count": total,
                "percentage": round(present / total * 100, 2) if total else 0.0,
            }
        )

    overall_total = total_present + total_absent
    return {
        "subjects": summary,
        "overall_percentage": (
            round(total_present / overall_total * 100, 2) if overall_total else 0.0
        ),
    }


def get_student_attendance_history(
    db: Session,
    student: Student,
    subject_id: int | None = None,
) -> list[dict]:
    query = (
        db.query(Attendance)
        .filter(Attendance.student_id == student.id)
    )
    if subject_id is not None:
        query = query.filter(Attendance.subject_id == subject_id)
    rows = query.order_by(Attendance.date.desc(), Attendance.time.desc(), Attendance.id.desc()).all()
    return [
        {
            "date": row.date,
            "time": row.time,
            "subject_name": row.subject.name,
            "status": row.status,
        }
        for row in rows
    ]
