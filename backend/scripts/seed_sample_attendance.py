import random
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database.database import engine
from app.models import (
    AcademicYear,
    Attendance,
    AttendanceSession,
    Faculty,
    Student,
    Subject,
    TimetableEntry,
    User,
)
from app.models.enums import AttendanceStatus, Period, SessionStatus, SubjectType, WeekDay

REAL_DB_PATH = BACKEND_DIR / "smart_attendance.db"
SAMPLE_START = date(2026, 10, 19)
SAMPLE_END = date(2026, 11, 11)
TODAY = date(2026, 11, 12)
SAMPLE_SESSIONS_PER_YEAR = 7
RANDOM_SEED = 42

PERIOD_WINDOWS = {
    Period.P1: (time(9, 0), time(10, 0)),
    Period.P2: (time(10, 0), time(11, 0)),
    Period.P3: (time(11, 0), time(12, 0)),
    Period.P4: (time(13, 0), time(14, 0)),
    Period.P5: (time(14, 0), time(15, 0)),
    Period.P6: (time(15, 0), time(16, 0)),
}
WEEKDAY_NUMBER = {
    WeekDay.MONDAY: 0,
    WeekDay.TUESDAY: 1,
    WeekDay.WEDNESDAY: 2,
    WeekDay.THURSDAY: 3,
    WeekDay.FRIDAY: 4,
}
PERIOD_NUMBER = {period: index for index, period in enumerate(Period)}
PROTECTED_MODELS = (Student, User, Subject, TimetableEntry)


@dataclass
class SampleJob:
    year: AcademicYear
    subject: Subject
    entry: TimetableEntry
    session_date: date
    existing_session: AttendanceSession | None


def ensure_real_database():
    database_path = Path(engine.url.database)
    resolved = database_path if database_path.is_absolute() else BACKEND_DIR / database_path
    if resolved.resolve() != REAL_DB_PATH.resolve():
        raise RuntimeError(
            f"Refusing to seed: DATABASE_URL must point to {REAL_DB_PATH}, got {resolved.resolve()}"
        )


def count_protected_rows(db):
    return {model.__tablename__: db.query(model).count() for model in PROTECTED_MODELS}


def weekdays_in_range(weekday):
    days = []
    current = SAMPLE_START
    while current <= SAMPLE_END:
        if current.weekday() == WEEKDAY_NUMBER[weekday]:
            days.append(current)
        current += timedelta(days=1)
    return days


def period_datetime(session_date, period, start=True):
    start_clock, end_clock = PERIOD_WINDOWS[period]
    clock = start_clock if start else end_clock
    offset = timedelta(minutes=5 if start else -5)
    return datetime.combine(session_date, clock) + offset


def mca_years(db):
    rows = (
        db.query(AcademicYear)
        .join(AcademicYear.programme)
        .filter(AcademicYear.programme.has(name="MCA"))
        .order_by(AcademicYear.id)
        .all()
    )
    years = {row.name: row for row in rows}
    if len(rows) != 2 or set(years) != {"1st Year", "2nd Year"}:
        raise RuntimeError(f"Expected MCA 1st and 2nd Year only; found {list(years)}")
    return years


def build_sample_jobs(db, years):
    jobs = []
    for year_name in ("1st Year", "2nd Year"):
        year = years[year_name]
        subjects = (
            db.query(Subject)
            .filter(Subject.academic_year_id == year.id)
            .order_by(Subject.id)
            .all()
        )
        if not subjects:
            raise RuntimeError(f"{year_name} has no subjects.")

        subject_types = {
            subject.subject_type.value
            if hasattr(subject.subject_type, "value")
            else str(subject.subject_type).upper()
            for subject in subjects
        }
        if not {SubjectType.THEORY.value, SubjectType.LAB.value}.issubset(subject_types):
            raise RuntimeError(f"{year_name} must contain both THEORY and LAB subjects.")

        selected_subjects = list(subjects[:SAMPLE_SESSIONS_PER_YEAR])
        while len(selected_subjects) < SAMPLE_SESSIONS_PER_YEAR:
            selected_subjects.append(subjects[(len(selected_subjects) - len(subjects)) % len(subjects)])

        used_dates = set()
        for index, subject in enumerate(selected_subjects):
            entries = (
                db.query(TimetableEntry)
                .filter(
                    TimetableEntry.academic_year_id == year.id,
                    TimetableEntry.subject_id == subject.id,
                )
                .all()
            )
            if not entries:
                raise RuntimeError(f"Subject {subject.code} has no timetable entries.")
            entry = min(
                entries,
                key=lambda row: (PERIOD_NUMBER[row.period], row.id),
            )
            matching_dates = weekdays_in_range(entry.day)
            target_day = SAMPLE_START + timedelta(
                days=round((SAMPLE_END - SAMPLE_START).days * index / (SAMPLE_SESSIONS_PER_YEAR - 1))
            )
            matching_dates.sort(key=lambda candidate: (abs((candidate - target_day).days), candidate))

            selected = None
            for candidate_date in matching_dates:
                if candidate_date in used_dates:
                    continue
                existing = (
                    db.query(AttendanceSession)
                    .filter(
                        AttendanceSession.timetable_entry_id == entry.id,
                        AttendanceSession.date == candidate_date,
                    )
                    .first()
                )
                if existing is not None and existing.status != SessionStatus.CLOSED:
                    continue
                selected = (candidate_date, existing)
                break
            if selected is None:
                raise RuntimeError(
                    f"Could not find an available past weekday for {year_name} / {subject.code}."
                )

            session_date, existing_session = selected
            used_dates.add(session_date)
            jobs.append(SampleJob(year, subject, entry, session_date, existing_session))

    return jobs


def build_attendance_plan(db, years, jobs, rng):
    plan = {}
    low_attendance_ids = {}
    for year_name in ("1st Year", "2nd Year"):
        year = years[year_name]
        students = (
            db.query(Student)
            .filter(Student.academic_year_id == year.id)
            .order_by(Student.id)
            .all()
        )
        low_students = [
            student for student in students if not student.face_registered
        ][:2]
        if len(students) < 3 or len(low_students) != 2:
            raise RuntimeError(
                f"{year_name} needs at least three students and two non-face-registered students."
            )
        low_attendance_ids[year.id] = {student.id for student in low_students}

        for student in students:
            if student.face_registered:
                present_count = SAMPLE_SESSIONS_PER_YEAR
            elif student.id in low_attendance_ids[year.id]:
                present_count = 4
            else:
                present_count = 6
            plan[(year.id, student.id)] = set(
                rng.sample(range(SAMPLE_SESSIONS_PER_YEAR), present_count)
            )

    if len(jobs) != SAMPLE_SESSIONS_PER_YEAR * len(years):
        raise RuntimeError(f"Expected 14 sample session jobs, found {len(jobs)}.")
    return plan, low_attendance_ids


def find_open_session_target(db, years):
    eligible_years = []
    for year in years.values():
        face_students = (
            db.query(Student)
            .filter(
                Student.academic_year_id == year.id,
                Student.face_registered.is_(True),
            )
            .order_by(Student.id)
            .all()
        )
        if face_students:
            eligible_years.append((year, face_students))
    if not eligible_years:
        raise RuntimeError("No MCA year contains a face-registered student.")

    open_sessions = (
        db.query(AttendanceSession)
        .filter(
            AttendanceSession.date == TODAY,
            AttendanceSession.status == SessionStatus.OPEN,
        )
        .order_by(AttendanceSession.id)
        .all()
    )
    if len(open_sessions) > 1:
        raise RuntimeError(f"Expected at most one OPEN session today; found {len(open_sessions)}.")
    if open_sessions:
        session = open_sessions[0]
        entry = (
            db.query(TimetableEntry)
            .filter(TimetableEntry.id == session.timetable_entry_id)
            .first()
        )
        if entry is None or entry.academic_year_id not in {year.id for year, _ in eligible_years}:
            raise RuntimeError("Today's existing OPEN session is not in an eligible face-registered year.")
        if entry.day != WeekDay.THURSDAY:
            raise RuntimeError("Today's existing OPEN session is not on a Thursday timetable entry.")
        faculty_user = (
            db.query(User)
            .filter(User.faculty_id == session.faculty_id)
            .order_by(User.id)
            .first()
        )
        if faculty_user is None:
            raise RuntimeError("Today's existing OPEN session faculty has no login.")
        if db.query(Attendance).filter(Attendance.attendance_session_id == session.id).count():
            raise RuntimeError("Today's existing OPEN session unexpectedly has attendance rows.")
        year = next(year for year, _ in eligible_years if year.id == entry.academic_year_id)
        face_students = next(students for candidate, students in eligible_years if candidate.id == year.id)
        return session, entry, year, faculty_user, face_students, False

    for year, face_students in eligible_years:
        entries = (
            db.query(TimetableEntry)
            .join(Faculty, Faculty.id == TimetableEntry.faculty_id)
            .filter(
                TimetableEntry.academic_year_id == year.id,
                TimetableEntry.day == WeekDay.THURSDAY,
            )
            .order_by(TimetableEntry.id)
            .all()
        )
        for entry in entries:
            faculty_user = (
                db.query(User)
                .filter(User.faculty_id == entry.faculty_id)
                .order_by(User.id)
                .first()
            )
            if faculty_user is not None:
                return None, entry, year, faculty_user, face_students, True
    raise RuntimeError(
        "No Thursday timetable entry in an MCA face-registered year has a faculty login."
    )


def main():
    ensure_real_database()
    if TODAY.weekday() != WEEKDAY_NUMBER[WeekDay.THURSDAY]:
        raise RuntimeError("Configured sample date is not a Thursday.")

    connection = engine.connect()
    outer_transaction = None
    db = None
    try:
        outer_transaction = connection.begin()
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        db = Session(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        protected_before = count_protected_rows(db)
        years = mca_years(db)
        jobs = build_sample_jobs(db, years)
        rng = random.Random(RANDOM_SEED)
        attendance_plan, low_attendance_ids = build_attendance_plan(db, years, jobs, rng)

        created_sessions = 0
        reused_sessions = 0
        created_attendance = 0
        sample_session_ids = []
        sample_session_ids_by_year = {year.id: [] for year in years.values()}
        for year_name in ("1st Year", "2nd Year"):
            year_jobs = [job for job in jobs if job.year.id == years[year_name].id]
            students = (
                db.query(Student)
                .filter(Student.academic_year_id == years[year_name].id)
                .order_by(Student.id)
                .all()
            )
            for slot_index, job in enumerate(year_jobs):
                session = job.existing_session
                if session is None:
                    session = AttendanceSession(
                        timetable_entry_id=job.entry.id,
                        faculty_id=job.entry.faculty_id,
                        subject_id=job.entry.subject_id,
                        academic_year_id=job.entry.academic_year_id,
                        date=job.session_date,
                        start_time=period_datetime(job.session_date, job.entry.period, start=True),
                        end_time=period_datetime(job.session_date, job.entry.period, start=False),
                        status=SessionStatus.CLOSED,
                    )
                    db.add(session)
                    db.flush()
                    created_sessions += 1

                    for student in students:
                        present = slot_index in attendance_plan[(job.year.id, student.id)]
                        attendance_time = session.start_time + timedelta(
                            minutes=rng.randint(1, 39)
                        )
                        db.add(
                            Attendance(
                                attendance_session_id=session.id,
                                student_id=student.id,
                                subject_id=session.subject_id,
                                faculty_id=session.faculty_id,
                                academic_year_id=session.academic_year_id,
                                date=session.date,
                                time=attendance_time,
                                status=(
                                    AttendanceStatus.PRESENT
                                    if present
                                    else AttendanceStatus.ABSENT
                                ),
                                timetable_entry_id=session.timetable_entry_id,
                            )
                        )
                        created_attendance += 1
                    db.flush()
                else:
                    reused_sessions += 1

                actual_rows = (
                    db.query(Attendance)
                    .filter(Attendance.attendance_session_id == session.id)
                    .count()
                )
                if actual_rows != len(students):
                    raise RuntimeError(
                        f"Closed sample session {session.id} has {actual_rows} attendance rows; "
                        f"expected {len(students)}."
                    )
                sample_session_ids.append(session.id)
                sample_session_ids_by_year[job.year.id].append(session.id)

        for year_name in ("1st Year", "2nd Year"):
            year = years[year_name]
            session_ids = sample_session_ids_by_year[year.id]
            students = (
                db.query(Student)
                .filter(Student.academic_year_id == year.id)
                .order_by(Student.id)
                .all()
            )
            low_ids = low_attendance_ids[year.id]
            for student in students:
                total = db.query(Attendance).filter(
                    Attendance.attendance_session_id.in_(session_ids),
                    Attendance.student_id == student.id,
                ).count()
                present = db.query(Attendance).filter(
                    Attendance.attendance_session_id.in_(session_ids),
                    Attendance.student_id == student.id,
                    Attendance.status == AttendanceStatus.PRESENT,
                ).count()
                percentage = present / total * 100 if total else 0
                if total != SAMPLE_SESSIONS_PER_YEAR:
                    raise RuntimeError(
                        f"Student {student.id} has {total}/{SAMPLE_SESSIONS_PER_YEAR} "
                        f"sample attendance rows."
                    )
                if student.face_registered and percentage < 85:
                    raise RuntimeError(
                        f"Face-registered student {student.id} attendance is only {percentage:.2f}%."
                    )
                if student.id in low_ids and not 55 <= percentage <= 70:
                    raise RuntimeError(
                        f"Low-attendance student {student.id} has {percentage:.2f}% attendance."
                    )
                if (
                    not student.face_registered
                    and student.id not in low_ids
                    and not 85 <= percentage <= 95
                ):
                    raise RuntimeError(
                        f"Student {student.id} expected 85-95% attendance, got {percentage:.2f}%."
                    )

        open_session, open_entry, open_year, open_faculty_user, face_students, create_open = (
            find_open_session_target(db, years)
        )
        if create_open:
            open_session = AttendanceSession(
                timetable_entry_id=open_entry.id,
                faculty_id=open_entry.faculty_id,
                subject_id=open_entry.subject_id,
                academic_year_id=open_entry.academic_year_id,
                date=TODAY,
                start_time=period_datetime(TODAY, open_entry.period, start=True),
                end_time=None,
                status=SessionStatus.OPEN,
            )
            db.add(open_session)
            db.flush()
        if db.query(Attendance).filter(
            Attendance.attendance_session_id == open_session.id
        ).count():
            raise RuntimeError("OPEN sample session must have no attendance rows.")

        db.flush()
        if count_protected_rows(db) != protected_before:
            raise RuntimeError("A protected table row count changed.")
        open_today_count = db.query(AttendanceSession).filter(
            AttendanceSession.date == TODAY,
            AttendanceSession.status == SessionStatus.OPEN,
        ).count()
        if open_today_count != 1:
            raise RuntimeError(f"Expected exactly one OPEN session today; found {open_today_count}.")

        db.commit()
        outer_transaction.commit()

        print("SAMPLE DATA")
        print(
            f"Created CLOSED sessions: {created_sessions}; "
            f"created attendance rows: {created_attendance}; reused CLOSED sessions: {reused_sessions}"
        )
        print(f"OPEN session created: {1 if create_open else 0}; reused: {0 if create_open else 1}")
        print(
            f"OPEN session id={open_session.id}, date={TODAY}, year={open_year.name}, "
            f"subject={open_entry.subject.name}, faculty_username={open_faculty_user.username}, "
            f"face_registered_students={[student.id for student in face_students]}"
        )
        print("Closed sample sessions: id | date | year | subject | present | absent")
        for session_id in sample_session_ids:
            session = db.query(AttendanceSession).filter(
                AttendanceSession.id == session_id
            ).one()
            present_count = db.query(Attendance).filter(
                Attendance.attendance_session_id == session.id,
                Attendance.status == AttendanceStatus.PRESENT,
            ).count()
            absent_count = db.query(Attendance).filter(
                Attendance.attendance_session_id == session.id,
                Attendance.status == AttendanceStatus.ABSENT,
            ).count()
            print(
                f"{session.id} | {session.date} | {session.academic_year.name} | "
                f"{session.subject.name} | {present_count} | {absent_count}"
            )
        print(
            "Low-attendance students: "
            + str(
                {
                    years[year_name].name: sorted(low_attendance_ids[years[year_name].id])
                    for year_name in ("1st Year", "2nd Year")
                }
            )
        )
        print("Transaction: COMMITTED")
    except Exception:
        if db is not None:
            db.rollback()
        if outer_transaction is not None and outer_transaction.is_active:
            outer_transaction.rollback()
        raise
    finally:
        if db is not None:
            db.close()
        connection.close()


if __name__ == "__main__":
    main()
