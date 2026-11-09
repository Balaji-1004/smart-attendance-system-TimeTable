import sys
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import create_access_token, hash_password
from app.database.database import SessionLocal, engine
from app.main import app
from app.models import (
    AcademicYear,
    Attendance,
    AttendanceSession,
    Department,
    Faculty,
    Student,
    Subject,
    TimetableEntry,
    User,
)
from app.models.enums import AttendanceStatus, SessionStatus
from app.models.user import Role


EXPECTED_DATABASE_NAME = "smart_attendance.test_copy.db"


def report(label, passed, details=""):
    print(f"{label}: {'PASS' if passed else 'FAIL'}" + (f" - {details}" if details else ""))


def ensure_test_database():
    database_path = Path(engine.url.database)
    if database_path.name != EXPECTED_DATABASE_NAME:
        raise RuntimeError(
            f"Refusing to run: DATABASE_URL must use {EXPECTED_DATABASE_NAME}, got {database_path.name}"
        )
    resolved = database_path if database_path.is_absolute() else BACKEND_DIR / database_path
    if resolved.resolve().parent != BACKEND_DIR.resolve():
        raise RuntimeError(f"Refusing to run outside backend: {resolved.resolve()}")
    return resolved.resolve()


def token_for(user):
    return create_access_token({"sub": str(user.id)})


def get_or_create_other_department_hod(db, department):
    existing = (
        db.query(User)
        .filter(User.role == Role.HOD, User.department_id == department.id)
        .order_by(User.id)
        .first()
    )
    if existing is not None:
        return existing
    suffix = uuid4().hex[:8]
    user = User(
        username=f"flow.other.hod.{suffix}",
        password_hash=hash_password(f"flow-{suffix}-password"),
        role=Role.HOD,
        department_id=department.id,
    )
    db.add(user)
    db.flush()
    return user


def prepare_fixtures(db):
    cs_department = db.query(Department).order_by(Department.id).first()
    if cs_department is None:
        raise RuntimeError("The first department is missing from the test copy.")

    cs_hod = (
        db.query(User)
        .filter(User.role == Role.HOD, User.department_id == cs_department.id)
        .order_by(User.id)
        .first()
    )
    if cs_hod is None:
        raise RuntimeError("The first-department HOD is missing from the test copy.")

    other_department = (
        db.query(Department)
        .filter(Department.id != cs_department.id)
        .order_by(Department.id)
        .first()
    )
    if other_department is None:
        raise RuntimeError("A second department is required for the isolation checks.")
    other_hod = get_or_create_other_department_hod(db, other_department)

    today = date.today()
    selected = None
    candidate_entries = (
        db.query(TimetableEntry)
        .join(AcademicYear, AcademicYear.id == TimetableEntry.academic_year_id)
        .filter(AcademicYear.department_id == cs_department.id)
        .order_by(AcademicYear.id, TimetableEntry.id)
        .all()
    )
    for entry in candidate_entries:
        faculty_user = (
            db.query(User)
            .filter(User.role == Role.FACULTY, User.faculty_id == entry.faculty_id)
            .first()
        )
        if faculty_user is None:
            continue
        open_session = (
            db.query(AttendanceSession)
            .filter(
                AttendanceSession.timetable_entry_id == entry.id,
                AttendanceSession.date == today,
                AttendanceSession.status == SessionStatus.OPEN,
            )
            .first()
        )
        if open_session is not None:
            continue
        other_faculty_user = (
            db.query(User)
            .join(Faculty, Faculty.id == User.faculty_id)
            .filter(
                User.role == Role.FACULTY,
                User.faculty_id != entry.faculty_id,
                Faculty.department_id == cs_department.id,
            )
            .order_by(User.id)
            .first()
        )
        if other_faculty_user is not None:
            selected = (entry, faculty_user, other_faculty_user)
            break
    if selected is None:
        raise RuntimeError("No first-department timetable entry with an available owner and a second faculty user.")

    entry, faculty_user, other_faculty_user = selected
    year = db.query(AcademicYear).filter(AcademicYear.id == entry.academic_year_id).first()
    other_year_student = (
        db.query(Student)
        .filter(
            Student.department_id == cs_department.id,
            Student.academic_year_id != year.id,
        )
        .order_by(Student.id)
        .first()
    )
    if other_year_student is None:
        raise RuntimeError("A first-department student from another academic year is required.")

    suffix = uuid4().hex[:10]
    student_a = Student(
        roll_number=f"FLOW-A-{suffix}",
        name="Flow Test Student A",
        email=f"flow-a-{suffix}@example.invalid",
        academic_year_id=year.id,
        department_id=cs_department.id,
        face_registered=False,
    )
    student_b = Student(
        roll_number=f"FLOW-B-{suffix}",
        name="Flow Test Student B",
        email=f"flow-b-{suffix}@example.invalid",
        academic_year_id=year.id,
        department_id=cs_department.id,
        face_registered=False,
    )
    db.add_all((student_a, student_b))
    db.flush()
    student_user = User(
        username=f"flow.student.{suffix}",
        password_hash=hash_password(f"flow-{suffix}-password"),
        role=Role.STUDENT,
        student_id=student_a.id,
    )
    db.add(student_user)
    db.flush()
    student_a.user_id = student_user.id
    db.commit()
    for record in (
        cs_hod,
        other_hod,
        faculty_user,
        other_faculty_user,
        student_a,
        student_b,
        student_user,
        other_year_student,
        year,
        entry,
        cs_department,
        other_department,
    ):
        db.refresh(record)

    return {
        "department": cs_department,
        "other_department": other_department,
        "hod": cs_hod,
        "other_hod": other_hod,
        "faculty_user": faculty_user,
        "other_faculty_user": other_faculty_user,
        "student_user": student_user,
        "student_a": student_a,
        "student_b": student_b,
        "other_year_student": other_year_student,
        "year": year,
        "entry": entry,
        "subject_name": entry.subject.name,
    }


def summary_matches_database(db, response_json, student, year):
    subjects = db.query(Subject).filter(Subject.academic_year_id == year.id).order_by(Subject.id).all()
    expected_subjects = []
    present_total = 0
    absent_total = 0
    for subject in subjects:
        statuses = (
            db.query(Attendance.status)
            .filter(
                Attendance.student_id == student.id,
                Attendance.subject_id == subject.id,
            )
            .all()
        )
        present = sum(1 for (value,) in statuses if value == AttendanceStatus.PRESENT)
        absent = sum(1 for (value,) in statuses if value == AttendanceStatus.ABSENT)
        total = present + absent
        present_total += present
        absent_total += absent
        expected_subjects.append(
            {
                "subject_id": subject.id,
                "subject_name": subject.name,
                "present_count": present,
                "absent_count": absent,
                "total_count": total,
                "percentage": round(present / total * 100, 2) if total else 0.0,
            }
        )
    total = present_total + absent_total
    expected_overall = round(present_total / total * 100, 2) if total else 0.0
    return response_json == {
        "subjects": expected_subjects,
        "overall_percentage": expected_overall,
    }


def run():
    database_path = ensure_test_database()
    print(f"Test database: {database_path}")
    db = SessionLocal()
    try:
        data = prepare_fixtures(db)
    finally:
        db.close()

    hod_headers = {"Authorization": f"Bearer {token_for(data['hod'])}"}
    other_hod_headers = {"Authorization": f"Bearer {token_for(data['other_hod'])}"}
    faculty_headers = {"Authorization": f"Bearer {token_for(data['faculty_user'])}"}
    other_faculty_headers = {"Authorization": f"Bearer {token_for(data['other_faculty_user'])}"}
    student_headers = {"Authorization": f"Bearer {token_for(data['student_user'])}"}
    passed = []

    with TestClient(app) as client:
        session_response = client.post(
            "/attendance-sessions",
            json={"timetable_entry_id": data["entry"].id},
            headers=faculty_headers,
        )
        session_id = session_response.json().get("id") if session_response.status_code == 200 else None
        other_faculty_start = client.post(
            "/attendance-sessions",
            json={"timetable_entry_id": data["entry"].id},
            headers=other_faculty_headers,
        )
        ok = session_response.status_code == 200 and other_faculty_start.status_code == 403
        passed.append(ok)
        report(
            "a. Faculty session ownership",
            ok,
            f"owner start={session_response.status_code}, other faculty start={other_faculty_start.status_code}",
        )
        if session_id is None:
            print("OVERALL: FAIL (cannot continue without a session)")
            return False

        mark_a = client.post(
            f"/attendance-sessions/{session_id}/mark",
            json={"student_id": data["student_a"].id},
            headers=faculty_headers,
        )
        mark_b = client.post(
            f"/attendance-sessions/{session_id}/mark",
            json={"student_id": data["student_b"].id},
            headers=faculty_headers,
        )
        duplicate_mark = client.post(
            f"/attendance-sessions/{session_id}/mark",
            json={"student_id": data["student_a"].id},
            headers=faculty_headers,
        )
        wrong_year_mark = client.post(
            f"/attendance-sessions/{session_id}/mark",
            json={"student_id": data["other_year_student"].id},
            headers=faculty_headers,
        )
        ok = (
            mark_a.status_code == 200
            and mark_b.status_code == 200
            and duplicate_mark.status_code == 400
            and wrong_year_mark.status_code == 400
        )
        passed.append(ok)
        report(
            "b. Present marks, duplicate rejection, and wrong-year rejection",
            ok,
            f"student A={mark_a.status_code}, student B={mark_b.status_code}, "
            f"duplicate={duplicate_mark.status_code}, wrong year={wrong_year_mark.status_code}",
        )

        duplicate_session = client.post(
            "/attendance-sessions",
            json={"timetable_entry_id": data["entry"].id},
            headers=faculty_headers,
        )
        close_response = client.put(f"/attendance-sessions/{session_id}/close", headers=faculty_headers)
        post_close_mark = client.post(
            f"/attendance-sessions/{session_id}/mark",
            json={"student_id": data["student_a"].id},
            headers=faculty_headers,
        )
        db = SessionLocal()
        try:
            enrolled_count = db.query(Student).filter(Student.academic_year_id == data["year"].id).count()
            marked_rows = (
                db.query(Attendance)
                .filter(Attendance.attendance_session_id == session_id)
                .all()
            )
            expected_absent = enrolled_count - 2
            actual_absent = sum(1 for row in marked_rows if row.status == AttendanceStatus.ABSENT)
        finally:
            db.close()
        second_session = client.post(
            "/attendance-sessions",
            json={"timetable_entry_id": data["entry"].id},
            headers=faculty_headers,
        )
        second_session_id = second_session.json().get("id") if second_session.status_code == 200 else None
        if second_session_id is not None:
            client.put(f"/attendance-sessions/{second_session_id}/close", headers=faculty_headers)
        ok = (
            duplicate_session.status_code == 400
            and close_response.status_code == 200
            and post_close_mark.status_code == 400
            and actual_absent == expected_absent
            and second_session.status_code == 200
        )
        passed.append(ok)
        report(
            "c. Close backfill, closed-session rejection, and reopen after close",
            ok,
            f"while open second start={duplicate_session.status_code}, close={close_response.status_code}, "
            f"absent={actual_absent}/{expected_absent}, mark after close={post_close_mark.status_code}, "
            f"start after close={second_session.status_code}",
        )

        summary_response = client.get("/me/attendance/summary", headers=student_headers)
        history_response = client.get("/me/attendance/history", headers=student_headers)
        filtered_history_response = client.get(
            f"/me/attendance/history?subject_id={data['entry'].subject_id}",
            headers=student_headers,
        )
        db = SessionLocal()
        try:
            summary_ok = summary_response.status_code == 200 and summary_matches_database(
                db,
                summary_response.json(),
                data["student_a"],
                data["year"],
            )
            b_has_rows = (
                db.query(Attendance)
                .filter(
                    Attendance.attendance_session_id == session_id,
                    Attendance.student_id == data["student_b"].id,
                )
                .count()
                > 0
            )
            own_rows = (
                db.query(Attendance)
                .filter(Attendance.student_id == data["student_a"].id)
                .order_by(Attendance.date.desc(), Attendance.time.desc(), Attendance.id.desc())
                .all()
            )
            expected_history = [
                (row.date, row.time, row.subject.name, row.status.value)
                for row in own_rows
            ]
            filtered_count = (
                db.query(Attendance)
                .filter(
                    Attendance.student_id == data["student_a"].id,
                    Attendance.subject_id == data["entry"].subject_id,
                )
                .count()
            )
        finally:
            db.close()
        history_json = history_response.json() if history_response.status_code == 200 else []
        actual_history = [
            (
                date.fromisoformat(row["date"]),
                datetime.fromisoformat(row["time"]),
                row["subject_name"],
                row["status"],
            )
            for row in history_json
        ]
        history_keys = [(row["date"], row["time"]) for row in history_json]
        history_sorted = all(left >= right for left, right in zip(history_keys, history_keys[1:]))
        filtered_history = (
            filtered_history_response.json()
            if filtered_history_response.status_code == 200
            else []
        )
        history_ok = (
            history_response.status_code == 200
            and b_has_rows
            and actual_history == expected_history
            and history_sorted
            and filtered_history_response.status_code == 200
            and len(filtered_history) == filtered_count
            and all(row["subject_name"] == data["subject_name"] for row in filtered_history)
        )
        ok = summary_ok and history_ok
        passed.append(ok)
        report(
            "d. Student summary matches DB and history omits another student's rows",
            ok,
            f"summary={summary_response.status_code}, exact DB match={summary_ok}, "
            f"history={history_response.status_code}, owned rows exact={actual_history == expected_history}, "
            f"newest-first={history_sorted}, subject filter={filtered_history_response.status_code}/"
            f"{len(filtered_history)} of {filtered_count}, other student's rows present in DB={b_has_rows}",
        )

        report_responses = [
            client.get(
                f"/reports/attendance/daily?date={date.today().isoformat()}",
                headers=student_headers,
            ),
            client.get(
                f"/reports/attendance/subject/{data['entry'].subject_id}",
                headers=student_headers,
            ),
            client.get(
                f"/reports/attendance/student/{data['student_a'].id}",
                headers=student_headers,
            ),
            client.get(
                f"/reports/attendance/class-summary/{data['year'].id}",
                headers=student_headers,
            ),
        ]
        generate = client.post(
            "/timetable/generate",
            json={"academic_year_id": data["year"].id},
            headers=student_headers,
        )
        sessions_list = client.get("/attendance-sessions", headers=student_headers)
        ok = all(response.status_code == 403 for response in (*report_responses, generate, sessions_list))
        passed.append(ok)
        report(
            "e. Student role is forbidden from reports, generation, and sessions",
            ok,
            f"reports={[response.status_code for response in report_responses]}, "
            f"generate={generate.status_code}, sessions={sessions_list.status_code}",
        )

        cross_session = client.get(
            f"/attendance-sessions/{session_id}",
            headers=other_hod_headers,
        )
        cross_report = client.get(
            f"/reports/attendance/student/{data['student_a'].id}",
            headers=other_hod_headers,
        )
        ok = cross_session.status_code == 404 and cross_report.status_code == 404
        passed.append(ok)
        report(
            "f. Other-department HOD receives 404 for session and report rows",
            ok,
            f"session={cross_session.status_code}, report rows={cross_report.status_code}",
        )

        timetable_response = client.get("/me/timetable", headers=student_headers)
        timetable_rows = timetable_response.json() if timetable_response.status_code == 200 else []
        db = SessionLocal()
        try:
            expected_entry_count = (
                db.query(TimetableEntry)
                .filter(TimetableEntry.academic_year_id == data["year"].id)
                .count()
            )
        finally:
            db.close()
        ok = (
            timetable_response.status_code == 200
            and len(timetable_rows) == expected_entry_count
            and all(row["academic_year_id"] == data["year"].id for row in timetable_rows)
        )
        passed.append(ok)
        report(
            "g. Student timetable is limited to the student's academic year",
            ok,
            f"status={timetable_response.status_code}, rows={len(timetable_rows)}/{expected_entry_count}, "
            f"year ids={sorted({row['academic_year_id'] for row in timetable_rows})}",
        )

        department_results = []
        role_headers = [
            ("HOD", hod_headers, data["department"]),
            ("FACULTY", faculty_headers, data["department"]),
            ("STUDENT", student_headers, data["department"]),
        ]
        for role, headers, department in role_headers:
            response = client.get("/departments/me", headers=headers)
            body = response.json() if response.status_code == 200 else {}
            valid = response.status_code == 200 and body == {
                "id": department.id,
                "name": department.name,
            }
            department_results.append(valid)
            report(
                f"h. /departments/me for {role}",
                valid,
                f"status={response.status_code}, department={body}",
            )
        other_department_response = client.get("/departments/me", headers=other_hod_headers)
        other_department_body = (
            other_department_response.json() if other_department_response.status_code == 200 else {}
        )
        other_department_ok = (
            other_department_response.status_code == 200
            and other_department_body == {
                "id": data["other_department"].id,
                "name": data["other_department"].name,
            }
        )
        report(
            "h. /departments/me for second-department HOD",
            other_department_ok,
            f"status={other_department_response.status_code}, department={other_department_body}",
        )
        passed.extend(department_results)
        passed.append(other_department_ok)

        profile_response = client.get("/me/profile", headers=student_headers)
        profile = profile_response.json() if profile_response.status_code == 200 else {}
        profile_ok = (
            profile_response.status_code == 200
            and profile.get("name") == data["student_a"].name
            and profile.get("roll_number") == data["student_a"].roll_number
            and profile.get("academic_year_name") == data["year"].name
            and profile.get("department_name") == data["department"].name
            and profile.get("face_registered") is False
        )
        passed.append(profile_ok)
        report("Student self profile", profile_ok, f"status={profile_response.status_code}, body={profile}")

    all_passed = all(passed)
    print(f"OVERALL: {'PASS' if all_passed else 'FAIL'} ({sum(passed)}/{len(passed)} checks)")
    return all_passed


if __name__ == "__main__":
    try:
        sys.exit(0 if run() else 1)
    except Exception as exc:
        print(f"OVERALL: FAIL ({type(exc).__name__}: {exc})")
        raise
