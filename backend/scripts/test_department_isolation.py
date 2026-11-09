import sys
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from app.core.security import create_access_token, decode_access_token, hash_password
from app.database.database import SessionLocal, engine
from app.main import app
from app.models import (
    AcademicYear,
    Department,
    Faculty,
    FacultyAvailability,
    Lab,
    Student,
    Subject,
    TimetableEntry,
    User,
)
from app.models.enums import Period, SubjectType, WeekDay
from app.models.user import Role
from app.services.timetable_validator import check_lab_concurrency
from create_department import create_department


def report(label, passed, details=""):
    print(f"{label}: {'PASS' if passed else 'FAIL'}" + (f" - {details}" if details else ""))


def token_for(user):
    # Deliberately use a contradictory token claim; department ownership is DB-derived.
    claimed_department_id = 1 if user.department_id != 1 else 999999
    return create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
            "department_id": claimed_department_id,
            "faculty_id": user.faculty_id,
            "student_id": user.student_id,
        }
    )


def new_test_data(db):
    if Path(engine.url.database).name != "smart_attendance.test_copy.db":
        raise RuntimeError(
            "Refusing to run: DATABASE_URL must point to backend/smart_attendance.test_copy.db"
        )

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
    cs_year = db.query(AcademicYear).filter(AcademicYear.department_id == cs_department.id).order_by(AcademicYear.id).first()
    cs_student = db.query(Student).filter(Student.department_id == cs_department.id).order_by(Student.id).first()
    cs_faculty = db.query(Faculty).filter(Faculty.department_id == cs_department.id).order_by(Faculty.id).first()
    cs_subject = (
        db.query(Subject)
        .join(AcademicYear, AcademicYear.id == Subject.academic_year_id)
        .filter(AcademicYear.department_id == cs_department.id)
        .order_by(Subject.id)
        .first()
    )
    cs_lab = db.query(Lab).filter(Lab.department_id == cs_department.id).order_by(Lab.id).first()
    cs_availability = (
        db.query(FacultyAvailability)
        .join(Faculty, Faculty.id == FacultyAvailability.faculty_id)
        .filter(Faculty.department_id == cs_department.id)
        .order_by(FacultyAvailability.id)
        .first()
    )
    cs_entry = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.academic_year_id == cs_year.id)
        .order_by(TimetableEntry.id)
        .first()
        if cs_year is not None
        else None
    )
    if not all((cs_year, cs_student, cs_faculty, cs_subject, cs_lab, cs_entry)):
        raise RuntimeError("First-department test fixtures are incomplete.")

    test_department, _ = create_department(
        db,
        "Test Dept B",
        "test-dept-b-hod",
        "test-password",
        ["1st Year", "2nd Year", "3rd Year"],
    )
    year = (
        db.query(AcademicYear)
        .filter(AcademicYear.department_id == test_department.id)
        .order_by(AcademicYear.id)
        .first()
    )
    faculty = Faculty(
        department_id=test_department.id,
        name="Test B Faculty",
        faculty_code="TEST-B-FAC",
        email="test-b-faculty@example.invalid",
    )
    lab = Lab(
        department_id=test_department.id,
        lab_code="TEST-B-LAB",
        name="Test B Lab",
    )
    db.add_all((faculty, lab))
    db.flush()
    subject = Subject(
        academic_year_id=year.id,
        name="Test B Lab Subject",
        code="TEST-B-SUB",
        subject_type=SubjectType.LAB.value,
        weekly_periods=3,
        faculty_id=faculty.id,
    )
    student = Student(
        roll_number="TEST-B-001",
        name="Test B Student",
        email="test-b-student@example.invalid",
        academic_year_id=year.id,
        department_id=test_department.id,
        face_registered=False,
    )
    db.add(student)
    db.flush()
    faculty_user = User(
        username="test-dept-b-faculty",
        password_hash=hash_password("test-password"),
        role=Role.FACULTY,
        faculty_id=faculty.id,
    )
    student_user = User(
        username="test-dept-b-student",
        password_hash=hash_password("test-password"),
        role=Role.STUDENT,
        student_id=student.id,
    )
    db.add_all((subject, faculty_user, student_user))
    db.commit()
    hod = (
        db.query(User)
        .filter(User.username == "test-dept-b-hod", User.role == Role.HOD)
        .first()
    )
    if hod is None:
        raise RuntimeError("Test department HOD was not created.")
    db.refresh(hod)

    return {
        "cs_department_id": cs_department.id,
        "cs_hod_token": token_for(cs_hod),
        "cs_year_id": cs_year.id,
        "cs_student_id": cs_student.id,
        "cs_faculty_id": cs_faculty.id,
        "cs_subject_id": cs_subject.id,
        "cs_lab_id": cs_lab.id,
        "cs_availability_id": cs_availability.id if cs_availability is not None else None,
        "cs_entry_id": cs_entry.id,
        "department_id": test_department.id,
        "hod_token": token_for(hod),
        "faculty_username": faculty_user.username,
        "student_username": student_user.username,
        "year_id": year.id,
        "student_id": student.id,
        "faculty_id": faculty.id,
        "subject_id": subject.id,
        "lab_id": lab.id,
    }


def check_resource_matrix(client, headers, label, endpoint, record_id, update_payload):
    listing = client.get(endpoint, headers=headers)
    list_json = listing.json() if listing.status_code == 200 else None
    list_pass = listing.status_code == 200 and all(
        row.get("id") != record_id for row in (list_json or [])
    )
    get_response = client.get(f"{endpoint}/{record_id}", headers=headers)
    update_response = client.put(
        f"{endpoint}/{record_id}",
        json=update_payload,
        headers=headers,
    )
    delete_response = client.delete(f"{endpoint}/{record_id}", headers=headers)
    passed = (
        list_pass
        and get_response.status_code == 404
        and update_response.status_code == 404
        and delete_response.status_code == 404
    )
    report(
        f"{label} {endpoint}",
        passed,
        f"list={listing.status_code}, get={get_response.status_code}, "
        f"update={update_response.status_code}, delete={delete_response.status_code}",
    )
    return passed


def run():
    db = SessionLocal()
    data = new_test_data(db)
    db.close()

    hod_b_headers = {"Authorization": f"Bearer {data['hod_token']}"}
    hod_cs_headers = {"Authorization": f"Bearer {data['cs_hod_token']}"}

    resource_specs = [
        ("academic-years", data["cs_year_id"], {"department_id": data["cs_department_id"], "name": "Changed"}),
        ("students", data["cs_student_id"], {"name": "Changed"}),
        ("faculty", data["cs_faculty_id"], {"name": "Changed"}),
        ("subjects", data["cs_subject_id"], {"name": "Changed"}),
        ("labs", data["cs_lab_id"], {"name": "Changed"}),
    ]
    passed = []
    with TestClient(app) as client:
        login_results = []
        for username in (
            "test-dept-b-hod",
            data["faculty_username"],
            data["student_username"],
        ):
            login = client.post(
                "/auth/login",
                json={"username": username, "password": "test-password"},
            )
            response_department_id = (
                login.json().get("department_id") if login.status_code == 200 else None
            )
            jwt_department_id = (
                decode_access_token(login.json()["access_token"]).get("department_id")
                if login.status_code == 200
                else None
            )
            login_results.append(
                login.status_code == 200
                and response_department_id == data["department_id"]
                and jwt_department_id == data["department_id"]
            )
            report(
                f"{username} login includes DB-derived department_id",
                login_results[-1],
                f"status={login.status_code}, response={response_department_id}, jwt={jwt_department_id}",
            )
        passed.extend(login_results)

        for endpoint, record_id, payload in resource_specs:
            passed.append(check_resource_matrix(
                client, hod_b_headers, "HOD-B cannot access first department", f"/{endpoint}", record_id, payload
            ))
        for endpoint, record_id, payload in [
            ("academic-years", data["year_id"], {"department_id": data["department_id"], "name": "Changed"}),
            ("students", data["student_id"], {"name": "Changed"}),
            ("faculty", data["faculty_id"], {"name": "Changed"}),
            ("subjects", data["subject_id"], {"name": "Changed"}),
            ("labs", data["lab_id"], {"name": "Changed"}),
        ]:
            passed.append(check_resource_matrix(
                client, hod_cs_headers, "First-department HOD cannot access B", f"/{endpoint}", record_id, payload
            ))

        face_status_from_b = client.get(
            f"/students/{data['cs_student_id']}/face-registration-status",
            headers=hod_b_headers,
        )
        face_status_from_cs = client.get(
            f"/students/{data['student_id']}/face-registration-status",
            headers=hod_cs_headers,
        )
        face_status_scoped = (
            face_status_from_b.status_code == 404
            and face_status_from_cs.status_code == 404
        )
        passed.append(face_status_scoped)
        report(
            "Face-registration status is department-scoped",
            face_status_scoped,
            f"cross statuses={face_status_from_b.status_code}/{face_status_from_cs.status_code}",
        )

        cross_faculty_availability = client.post(
            "/faculty-availability",
            json={"faculty_id": data["cs_faculty_id"], "day": "FRIDAY", "period": "P6"},
            headers=hod_b_headers,
        )
        b_availability = client.post(
            "/faculty-availability",
            json={"faculty_id": data["faculty_id"], "day": "FRIDAY", "period": "P6"},
            headers=hod_b_headers,
        )
        b_availability_id = b_availability.json().get("id") if b_availability.status_code == 200 else None
        cs_availability_list = client.get("/faculty-availability", headers=hod_cs_headers)
        b_availability_list = client.get("/faculty-availability", headers=hod_b_headers)
        cross_availability_delete = (
            client.delete(
                f"/faculty-availability/{b_availability_id}",
                headers=hod_cs_headers,
            )
            if b_availability_id is not None
            else None
        )
        availability_scoped = (
            cross_faculty_availability.status_code == 404
            and b_availability.status_code == 200
            and b_availability_id is not None
            and all(row["id"] != b_availability_id for row in cs_availability_list.json())
            and any(row["id"] == b_availability_id for row in b_availability_list.json())
            and cross_availability_delete is not None
            and cross_availability_delete.status_code == 404
        )
        passed.append(availability_scoped)
        report(
            "Faculty availability is department-scoped",
            availability_scoped,
            f"cross create={cross_faculty_availability.status_code}, B create={b_availability.status_code}, "
            f"cross delete={cross_availability_delete.status_code if cross_availability_delete else 'n/a'}",
        )

        cross_faculty_subject = client.post(
            "/subjects",
            json={
                "academic_year_id": data["year_id"],
                "name": "Invalid Cross Department Subject",
                "code": "TEST-B-CROSS",
                "subject_type": "THEORY",
                "weekly_periods": 1,
                "faculty_id": data["cs_faculty_id"],
            },
            headers=hod_b_headers,
        )
        passed.append(cross_faculty_subject.status_code == 400)
        report(
            "HOD-B cannot create a subject with first-department faculty",
            cross_faculty_subject.status_code == 400,
            f"status={cross_faculty_subject.status_code}, body={cross_faculty_subject.text}",
        )

        mismatch_year = client.post(
            "/academic-years",
            json={"department_id": data["cs_department_id"], "name": "Mismatch year"},
            headers=hod_b_headers,
        )
        passed.append(mismatch_year.status_code == 403)
        report(
            "Mismatched academic-year department is rejected",
            mismatch_year.status_code == 403,
            f"status={mismatch_year.status_code}",
        )
        cross_year_subject_update = client.put(
            f"/subjects/{data['subject_id']}",
            json={"academic_year_id": data["cs_year_id"]},
            headers=hod_b_headers,
        )
        passed.append(cross_year_subject_update.status_code == 404)
        report(
            "HOD-B cannot move a subject into a first-department academic year",
            cross_year_subject_update.status_code == 404,
            f"status={cross_year_subject_update.status_code}",
        )

        db = SessionLocal()
        cs_entry_count_before = (
            db.query(TimetableEntry)
            .filter(TimetableEntry.academic_year_id.in_(
                db.query(AcademicYear.id).filter(AcademicYear.department_id == data["cs_department_id"])
            ))
            .count()
        )
        db.close()
        generated = client.post(
            "/timetable/generate",
            json={"academic_year_id": data["year_id"]},
            headers=hod_b_headers,
        )
        db = SessionLocal()
        b_entries = (
            db.query(TimetableEntry)
            .filter(TimetableEntry.academic_year_id == data["year_id"])
            .all()
        )
        b_lab_ids = {row.lab_id for row in b_entries if row.lab_id is not None}
        cs_entry_count_after = (
            db.query(TimetableEntry)
            .filter(TimetableEntry.academic_year_id.in_(
                db.query(AcademicYear.id).filter(AcademicYear.department_id == data["cs_department_id"])
            ))
            .count()
        )
        b_generation_ok = (
            generated.status_code == 200
            and len(b_entries) > 0
            and b_lab_ids == {data["lab_id"]}
            and cs_entry_count_before == cs_entry_count_after
        )
        passed.append(b_generation_ok)
        report(
            "HOD-B timetable generation uses only B labs; first-department count unchanged",
            b_generation_ok,
            f"status={generated.status_code}, placed={generated.json().get('placed_count') if generated.status_code == 200 else 'n/a'}, "
            f"B lab ids={sorted(b_lab_ids)}, first-department entries={cs_entry_count_before}->{cs_entry_count_after}",
        )
        b_timetable_entry_id = b_entries[0].id if b_entries else None
        b_year_timetable = client.get(
            f"/timetable/year/{data['year_id']}",
            headers=hod_b_headers,
        )
        cross_year_timetable = client.get(
            f"/timetable/year/{data['year_id']}",
            headers=hod_cs_headers,
        )
        cross_faculty_timetable = client.get(
            f"/timetable/faculty/{data['cs_faculty_id']}",
            headers=hod_b_headers,
        )
        b_department_timetable = client.get("/timetable/department", headers=hod_b_headers)
        cs_department_timetable = client.get("/timetable/department", headers=hod_cs_headers)
        cs_entry_update = client.put(
            f"/timetable/{data['cs_entry_id']}",
            json={"day": "FRIDAY", "period": "P6"},
            headers=hod_b_headers,
        )
        b_entry_update = (
            client.put(
                f"/timetable/{b_timetable_entry_id}",
                json={"day": "FRIDAY", "period": "P6"},
                headers=hod_cs_headers,
            )
            if b_timetable_entry_id is not None
            else None
        )
        b_cross_lab_update = (
            client.put(
                f"/timetable/{b_timetable_entry_id}",
                json={"lab_id": data["cs_lab_id"]},
                headers=hod_b_headers,
            )
            if b_timetable_entry_id is not None
            else None
        )
        cs_entry_delete = client.delete(
            f"/timetable/{data['cs_entry_id']}",
            headers=hod_b_headers,
        )
        b_entry_delete = (
            client.delete(
                f"/timetable/{b_timetable_entry_id}",
                headers=hod_cs_headers,
            )
            if b_timetable_entry_id is not None
            else None
        )
        timetable_scoped = (
            b_year_timetable.status_code == 200
            and cross_year_timetable.status_code == 404
            and cross_faculty_timetable.status_code == 404
            and all(row["academic_year_id"] == data["year_id"] for row in b_department_timetable.json())
            and all(row["academic_year_id"] != data["year_id"] for row in cs_department_timetable.json())
            and cs_entry_update.status_code == 404
            and b_entry_update is not None
            and b_entry_update.status_code == 404
            and b_cross_lab_update is not None
            and b_cross_lab_update.status_code == 404
            and cs_entry_delete.status_code == 404
            and b_entry_delete is not None
            and b_entry_delete.status_code == 404
        )
        passed.append(timetable_scoped)
        report(
            "Timetable year/faculty/department/update/delete are department-scoped",
            timetable_scoped,
            f"year={b_year_timetable.status_code}/{cross_year_timetable.status_code}, "
            f"cross faculty={cross_faculty_timetable.status_code}, entry update/delete="
            f"{cs_entry_update.status_code}/{b_entry_update.status_code if b_entry_update else 'n/a'}/"
            f"cross lab={b_cross_lab_update.status_code if b_cross_lab_update else 'n/a'}/"
            f"{cs_entry_delete.status_code}/{b_entry_delete.status_code if b_entry_delete else 'n/a'}",
        )

        cs_lab_slot = (
            db.query(TimetableEntry)
            .join(Lab, Lab.id == TimetableEntry.lab_id)
            .filter(Lab.department_id == data["cs_department_id"])
            .order_by(TimetableEntry.id)
            .first()
        )
        candidate_slot = None
        if cs_lab_slot is not None:
            for period in (cs_lab_slot.period,):
                occupied_in_b_year = (
                    db.query(TimetableEntry)
                    .filter(
                        TimetableEntry.academic_year_id == data["year_id"],
                        TimetableEntry.day == cs_lab_slot.day,
                        TimetableEntry.period == period,
                    )
                    .first()
                )
                if occupied_in_b_year is None:
                    candidate_slot = (cs_lab_slot.day, period)
                    break

        if candidate_slot is None:
            passed.append(False)
            report("Cross-department same-slot lab capacity", False, "No free B year period matching a first-department lab slot.")
        else:
            slot_day, slot_period = candidate_slot
            before_local_capacity, before_reason = check_lab_concurrency(
                db,
                slot_day,
                slot_period,
                lab_total_count=1,
                department_id=data["department_id"],
            )
            extra_entry = TimetableEntry(
                academic_year_id=data["year_id"],
                subject_id=data["subject_id"],
                faculty_id=data["faculty_id"],
                day=slot_day,
                period=slot_period,
                lab_id=data["lab_id"],
            )
            db.add(extra_entry)
            db.commit()
            after_local_capacity, after_reason = check_lab_concurrency(
                db,
                slot_day,
                slot_period,
                lab_total_count=1,
                department_id=data["department_id"],
            )
            same_slot_allowed = (
                before_local_capacity
                and not after_local_capacity
                and db.query(TimetableEntry)
                .filter(
                    TimetableEntry.academic_year_id == data["year_id"],
                    TimetableEntry.day == slot_day,
                    TimetableEntry.period == slot_period,
                    TimetableEntry.lab_id == data["lab_id"],
                )
                .count() == 1
            )
            passed.append(same_slot_allowed)
            report(
                "First-department and B lab use at same slot is allowed; extra B use exceeds B capacity",
                same_slot_allowed,
                f"First-department slot={slot_day.value}/{slot_period.value}, B capacity before={before_local_capacity} ({before_reason}), "
                f"additional B use after={after_local_capacity} ({after_reason})",
            )
        db.close()

        session_response = client.post(
            "/attendance-sessions",
            json={"timetable_entry_id": b_timetable_entry_id},
            headers=hod_b_headers,
        ) if b_timetable_entry_id is not None else None
        session_created = session_response is not None and session_response.status_code == 200
        if session_created:
            session_id = session_response.json()["id"]
            mark_response = client.post(
                f"/attendance-sessions/{session_id}/mark",
                json={"student_id": data["student_id"]},
                headers=hod_b_headers,
            )
            b_sessions = client.get("/attendance-sessions", headers=hod_b_headers).json()
            cs_sessions = client.get("/attendance-sessions", headers=hod_cs_headers).json()
            cs_session_get = client.get(f"/attendance-sessions/{session_id}", headers=hod_cs_headers)
            cross_start = client.post(
                "/attendance-sessions",
                json={"timetable_entry_id": data["cs_entry_id"]},
                headers=hod_b_headers,
            )
            today_report = client.get(
                f"/reports/attendance/daily?date={date.today().isoformat()}",
                headers=hod_b_headers,
            )
            cs_today_report = client.get(
                f"/reports/attendance/daily?date={date.today().isoformat()}",
                headers=hod_cs_headers,
            )
            cross_student_report = client.get(
                f"/reports/attendance/student/{data['student_id']}",
                headers=hod_cs_headers,
            )
            cross_year_report = client.get(
                f"/reports/attendance/class-summary/{data['year_id']}",
                headers=hod_cs_headers,
            )
            sessions_scoped = (
                mark_response.status_code == 200
                and any(row["id"] == session_id for row in b_sessions)
                and all(row["id"] != session_id for row in cs_sessions)
                and cs_session_get.status_code == 404
                and cross_start.status_code == 404
            )
            report_student_ids = {
                row["student_id"] for row in today_report.json()
            } if today_report.status_code == 200 else set()
            cs_report_student_ids = {
                row["student_id"] for row in cs_today_report.json()
            } if cs_today_report.status_code == 200 else set()
            reports_scoped = (
                data["student_id"] in report_student_ids
                and data["student_id"] not in cs_report_student_ids
                and cross_student_report.status_code == 404
                and cross_year_report.status_code == 404
            )
        else:
            session_id = None
            sessions_scoped = False
            reports_scoped = False
        passed.extend((sessions_scoped, reports_scoped))
        report(
            "Attendance sessions stay within the HOD department",
            sessions_scoped,
            f"create={session_response.status_code if session_response is not None else 'no B entry'}, "
            f"cross get={cs_session_get.status_code if session_created else 'n/a'}, "
            f"cross start={cross_start.status_code if session_created else 'n/a'}",
        )
        report(
            "Attendance reports stay within the HOD department",
            reports_scoped,
            f"B student in B daily report={data['student_id'] in report_student_ids if session_created else False}, "
            f"in first-department report={data['student_id'] in cs_report_student_ids if session_created else False}, "
            f"cross student/year statuses={cross_student_report.status_code if session_created else 'n/a'}/"
            f"{cross_year_report.status_code if session_created else 'n/a'}",
        )

        dashboard = client.get("/dashboard/hod", headers=hod_b_headers)
        if dashboard.status_code == 200:
            counts = dashboard.json()["counts"]
            dashboard_ok = (
                counts["academic_years"] == 3
                and counts["students"] == 1
                and counts["faculty"] == 1
                and counts["subjects"] == 1
                and counts["labs"] == 1
            )
            dashboard_detail = counts
        else:
            dashboard_ok = False
            dashboard_detail = dashboard.text
        passed.append(dashboard_ok)
        report(
            "HOD-B dashboard counts exclude first-department data",
            dashboard_ok,
            f"status={dashboard.status_code}, counts={dashboard_detail}",
        )

    print(f"OVERALL: {'PASS' if all(passed) else 'FAIL'} ({sum(passed)}/{len(passed)} checks)")
    return all(passed)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
