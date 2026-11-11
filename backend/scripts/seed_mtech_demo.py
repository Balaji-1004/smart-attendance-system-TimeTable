import hashlib
import secrets
import sys
from pathlib import Path

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import hash_password
from app.database.database import engine
from app.models import (
    AcademicYear,
    Attendance,
    AttendanceSession,
    Department,
    Faculty,
    FacultyAvailability,
    Lab,
    Programme,
    Student,
    Subject,
    TimetableEntry,
    User,
)
from app.models.enums import SubjectType
from app.models.user import Role
from app.services.timetable_generator import generate_timetable


EXPECTED_FACE_HASH = "0b051a6c5b0a253c5f5786da5a3fe656ecfb65ab93967ae58fd872d6718a5242"
BACKUP_PATH = BACKEND_DIR / "smart_attendance.backup_before_final_setup.db"
REAL_DB_PATH = BACKEND_DIR / "smart_attendance.db"
TEST_DB_PATH = BACKEND_DIR / "smart_attendance.test_copy.db"

FACULTY_SPECS = (
    ("FAC-MT-01", "Dr. Kavya Nair", "kavya.nair", "kavya.nair@demo.invalid"),
    ("FAC-MT-02", "Prof. Rajesh Menon", "rajesh.menon", "rajesh.menon@demo.invalid"),
    ("FAC-MT-03", "Ms. Divya Krishnan", "divya.krishnan", "divya.krishnan@demo.invalid"),
)
LAB_SPECS = (
    ("LAB-MT-01", "MTech Lab 1"),
    ("LAB-MT-02", "MTech Lab 2"),
)
SUBJECT_SPECS = (
    ("1st Year", "Advanced Algorithms", "THEORY", 3, "FAC-MT-01", "MT1-ALG"),
    ("1st Year", "Machine Learning", "THEORY", 3, "FAC-MT-02", "MT1-ML"),
    ("1st Year", "Research Methodology", "THEORY", 2, "FAC-MT-03", "MT1-RM"),
    ("1st Year", "ML Lab", "LAB", 3, "FAC-MT-03", "MT1-MLL"),
    ("2nd Year", "Deep Learning", "THEORY", 3, "FAC-MT-01", "MT2-DL"),
    ("2nd Year", "Cloud Computing", "THEORY", 3, "FAC-MT-02", "MT2-CC"),
    ("2nd Year", "Big Data Analytics", "THEORY", 2, "FAC-MT-03", "MT2-BDA"),
    ("2nd Year", "Data Lab", "LAB", 3, "FAC-MT-03", "MT2-DLB"),
)
STUDENT_SPECS = (
    ("1st Year", "MT1-001", "Aadhya Sharma", "mt1-001@students.demo.invalid", "mt1.demo"),
    ("1st Year", "MT1-002", "Arjun Iyer", "mt1-002@students.demo.invalid", None),
    ("1st Year", "MT1-003", "Meera Nair", "mt1-003@students.demo.invalid", None),
    ("1st Year", "MT1-004", "Rohan Pillai", "mt1-004@students.demo.invalid", None),
    ("2nd Year", "MT2-001", "Ananya Menon", "mt2-001@students.demo.invalid", "mt2.demo"),
    ("2nd Year", "MT2-002", "Kiran Rao", "mt2-002@students.demo.invalid", None),
    ("2nd Year", "MT2-003", "Nisha Kumar", "mt2-003@students.demo.invalid", None),
    ("2nd Year", "MT2-004", "Vivek Das", "mt2-004@students.demo.invalid", None),
)


def face_embedding_hash(db):
    digest = hashlib.sha256()
    rows = db.execute(
        text("SELECT student_id, face_embedding FROM face_data ORDER BY student_id")
    )
    for _, embedding in rows:
        if embedding is None:
            raise RuntimeError("A face_data.face_embedding value is NULL.")
        digest.update(bytes(embedding))
    return digest.hexdigest()


def table_counts(db):
    models = (
        ("users", User),
        ("faculty", Faculty),
        ("students", Student),
        ("face_data", "face_data"),
        ("subjects", Subject),
        ("timetable_entries", TimetableEntry),
        ("attendance_sessions", AttendanceSession),
        ("attendance", Attendance),
    )
    counts = {}
    for name, model in models:
        if model == "face_data":
            counts[name] = db.execute(text("SELECT COUNT(*) FROM face_data")).scalar_one()
        else:
            counts[name] = db.query(model).count()
    return counts


def department_counts(db, department_id):
    year_ids = db.query(AcademicYear.id).filter(
        AcademicYear.department_id == department_id
    )
    user_count = (
        db.query(User.id)
        .outerjoin(Faculty, User.faculty_id == Faculty.id)
        .outerjoin(Student, User.student_id == Student.id)
        .filter(
            or_(
                User.department_id == department_id,
                Faculty.department_id == department_id,
                Student.department_id == department_id,
            )
        )
        .distinct()
        .count()
    )
    return {
        "academic_years": db.query(AcademicYear).filter(
            AcademicYear.department_id == department_id
        ).count(),
        "students": db.query(Student).filter(Student.department_id == department_id).count(),
        "faculty": db.query(Faculty).filter(Faculty.department_id == department_id).count(),
        "users": user_count,
        "subjects": db.query(Subject)
        .filter(Subject.academic_year_id.in_(year_ids))
        .count(),
        "labs": db.query(Lab).filter(Lab.department_id == department_id).count(),
        "timetable_entries": db.query(TimetableEntry)
        .filter(TimetableEntry.academic_year_id.in_(year_ids))
        .count(),
        "attendance_sessions": db.query(AttendanceSession)
        .filter(AttendanceSession.academic_year_id.in_(year_ids))
        .count(),
        "attendance": db.query(Attendance)
        .filter(Attendance.academic_year_id.in_(year_ids))
        .count(),
        "face_data": db.execute(
            text(
                "SELECT COUNT(*) FROM face_data "
                "WHERE student_id IN (SELECT id FROM students WHERE department_id = :department_id)"
            ),
            {"department_id": department_id},
        ).scalar_one(),
    }


def check_real_database():
    database_path = Path(engine.url.database).resolve()
    if database_path == TEST_DB_PATH.resolve():
        return
    if database_path != REAL_DB_PATH.resolve():
        raise RuntimeError(
            f"Refusing to run: DATABASE_URL must point to {REAL_DB_PATH} "
            f"or {TEST_DB_PATH}, got {database_path}"
        )
    if not BACKUP_PATH.is_file():
        raise RuntimeError(f"Required backup is missing: {BACKUP_PATH}")


def resolve_departments(db):
    department = db.query(Department).filter(Department.name == "Computer Science").first()
    if department is None or department.id != 1:
        raise RuntimeError("Expected department Computer Science with id 1.")
    mca = db.query(Programme).filter(
        Programme.department_id == department.id,
        Programme.name == "MCA",
    ).first()
    mtech = db.query(Programme).filter(
        Programme.department_id == department.id,
        Programme.name == "MTech",
    ).first()
    if mca is None or mtech is None:
        raise RuntimeError("Expected MCA and MTech programmes in department 1.")
    return department, mca, mtech


def resolve_years(db, mtech):
    years = {}
    for year_name in ("1st Year", "2nd Year"):
        year = (
            db.query(AcademicYear)
            .filter(
                AcademicYear.programme_id == mtech.id,
                AcademicYear.name == year_name,
            )
            .first()
        )
        if year is None:
            raise RuntimeError(f"MTech academic year {year_name!r} is missing.")
        years[year_name] = year
    return years


def check_capacity(db, department, mtech, years):
    faculty_by_code = {}
    for code, _, _, email in FACULTY_SPECS:
        faculty = db.query(Faculty).filter(Faculty.faculty_code == code).first()
        if faculty is not None and faculty.department_id != department.id:
            raise RuntimeError(f"Faculty code {code} already belongs to another department.")
        if faculty is None:
            email_owner = db.query(Faculty).filter(Faculty.email == email).first()
            if email_owner is not None:
                raise RuntimeError(f"Faculty email {email} is already used by another faculty.")
            faculty_by_code[code] = ("new", code)
        else:
            faculty_by_code[code] = faculty.id

    mtech_year_ids = [
        row[0]
        for row in db.query(AcademicYear.id)
        .filter(AcademicYear.programme_id == mtech.id)
        .all()
    ]
    year_totals = dict(
        db.query(Subject.academic_year_id, func.coalesce(func.sum(Subject.weekly_periods), 0))
        .filter(Subject.academic_year_id.in_(mtech_year_ids))
        .group_by(Subject.academic_year_id)
        .all()
    )
    faculty_totals = dict(
        db.query(Subject.faculty_id, func.coalesce(func.sum(Subject.weekly_periods), 0))
        .join(Faculty, Faculty.id == Subject.faculty_id)
        .filter(Faculty.department_id == department.id)
        .group_by(Subject.faculty_id)
        .all()
    )

    for year_name, _, _, weekly_periods, faculty_code, code in SUBJECT_SPECS:
        year_id = years[year_name].id
        existing = (
            db.query(Subject)
            .filter(Subject.academic_year_id == year_id, Subject.code == code)
            .first()
        )
        if existing is not None:
            assigned_faculty = db.query(Faculty).filter(Faculty.id == existing.faculty_id).first()
            if assigned_faculty is None or assigned_faculty.department_id != department.id:
                raise RuntimeError(f"Existing MTech subject {code} uses a faculty outside MTech.")
            continue
        target_faculty = faculty_by_code[faculty_code]
        year_totals[year_id] = year_totals.get(year_id, 0) + weekly_periods
        faculty_totals[target_faculty] = faculty_totals.get(target_faculty, 0) + weekly_periods

    failures = []
    for year_id, total in year_totals.items():
        if total > 30:
            failures.append(f"academic_year_id={year_id}: {total} weekly periods exceeds 30")
    for faculty_key, total in faculty_totals.items():
        if total > 15:
            failures.append(f"faculty={faculty_key}: {total} weekly periods exceeds 15")
    if failures:
        raise RuntimeError("Capacity check failed: " + "; ".join(failures))


def ensure_faculty(db, department, credentials):
    faculties = {}
    for code, name, username, email in FACULTY_SPECS:
        faculty = db.query(Faculty).filter(Faculty.faculty_code == code).first()
        if faculty is None:
            faculty = Faculty(
                department_id=department.id,
                name=name,
                faculty_code=code,
                email=email,
            )
            db.add(faculty)
            db.flush()

        user = db.query(User).filter(User.username == username).first()
        if user is None:
            password = secrets.token_urlsafe(12)
            user = User(
                username=username,
                password_hash=hash_password(password),
                role=Role.FACULTY,
                department_id=department.id,
                faculty_id=faculty.id,
            )
            db.add(user)
            credentials.append((username, password))
        elif user.role != Role.FACULTY or user.faculty_id != faculty.id:
            raise RuntimeError(f"Username {username} already exists with a different account.")
        faculties[code] = faculty
    return faculties


def ensure_labs(db, department):
    for code, name in LAB_SPECS:
        lab = db.query(Lab).filter(Lab.lab_code == code).first()
        if lab is None:
            db.add(Lab(department_id=department.id, lab_code=code, name=name))
        elif lab.department_id != department.id:
            raise RuntimeError(f"Lab code {code} already belongs to another department.")
    db.flush()


def ensure_subjects(db, years, faculties):
    for year_name, name, subject_type, weekly_periods, faculty_code, code in SUBJECT_SPECS:
        subject = (
            db.query(Subject)
            .filter(
                Subject.academic_year_id == years[year_name].id,
                Subject.code == code,
            )
            .first()
        )
        if subject is None:
            db.add(
                Subject(
                    academic_year_id=years[year_name].id,
                    name=name,
                    code=code,
                    subject_type=SubjectType(subject_type).value,
                    weekly_periods=weekly_periods,
                    faculty_id=faculties[faculty_code].id,
                )
            )
        elif subject.faculty_id != faculties[faculty_code].id:
            raise RuntimeError(f"Existing subject {code} is assigned to a different faculty.")
    db.flush()


def ensure_students(db, department, years, credentials):
    for year_name, roll_number, name, email, username in STUDENT_SPECS:
        student = db.query(Student).filter(Student.roll_number == roll_number).first()
        if student is None:
            email_owner = db.query(Student).filter(Student.email == email).first()
            if email_owner is not None:
                raise RuntimeError(f"Student email {email} is already used by another student.")
            student = Student(
                roll_number=roll_number,
                name=name,
                email=email,
                academic_year_id=years[year_name].id,
                department_id=department.id,
                face_registered=False,
            )
            db.add(student)
            db.flush()
        elif (
            student.department_id != department.id
            or student.academic_year_id != years[year_name].id
        ):
            raise RuntimeError(f"Student roll number {roll_number} belongs to another department/year.")

        if username is None:
            continue
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            password = secrets.token_urlsafe(12)
            user = User(
                username=username,
                password_hash=hash_password(password),
                role=Role.STUDENT,
                department_id=department.id,
                student_id=student.id,
            )
            db.add(user)
            credentials.append((username, password))
        elif user.role != Role.STUDENT or user.student_id != student.id:
            raise RuntimeError(f"Username {username} already exists with a different account.")


def clean_mca_accounts(db):
    messages = []
    verify_user = db.query(User).filter(User.username == "verify.faculty").first()
    verify_faculty = None
    if verify_user is not None and verify_user.faculty_id is not None:
        verify_faculty = db.query(Faculty).filter(Faculty.id == verify_user.faculty_id).first()

    for username in ("hod01", "student01", "verify.faculty"):
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            messages.append(f"Cleanup {username}: skipped (not found)")
            continue
        if username == "student01":
            linked_students = (
                db.query(Student)
                .filter(or_(Student.user_id == user.id, Student.id == user.student_id))
                .all()
            )
            for student in linked_students:
                if student.user_id == user.id:
                    student.user_id = None
            if linked_students:
                db.flush()
                messages.append(
                    f"Cleanup student01: cleared user_id for {len(linked_students)} linked student row(s)"
                )
        db.delete(user)
        db.flush()
        messages.append(f"Cleanup {username}: deleted user")

    if verify_faculty is None:
        messages.append("Cleanup verify.faculty faculty row: skipped (no linked faculty row)")
        return messages

    counts = {
        "subjects": db.query(Subject).filter(Subject.faculty_id == verify_faculty.id).count(),
        "timetable_entries": db.query(TimetableEntry)
        .filter(TimetableEntry.faculty_id == verify_faculty.id)
        .count(),
        "availability": db.query(FacultyAvailability)
        .filter(FacultyAvailability.faculty_id == verify_faculty.id)
        .count(),
        "attendance": db.query(Attendance).filter(Attendance.faculty_id == verify_faculty.id).count(),
        "other_users": db.query(User)
        .filter(User.faculty_id == verify_faculty.id)
        .count(),
    }
    blockers = {key: value for key, value in counts.items() if value}
    if blockers:
        messages.append(f"Cleanup verify.faculty faculty row: kept; linked records remain {blockers}")
        return messages
    db.delete(verify_faculty)
    db.flush()
    messages.append("Cleanup verify.faculty faculty row: deleted (no linked records)")
    return messages


def main():
    check_real_database()
    print(
        f"Backup: {BACKUP_PATH} ({BACKUP_PATH.stat().st_size} bytes); "
        f"real DB: {REAL_DB_PATH} ({REAL_DB_PATH.stat().st_size} bytes)"
    )

    connection = engine.connect()
    outer_transaction = None
    db = None
    credentials = []
    try:
        outer_transaction = connection.begin()
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        db = Session(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        before_counts = table_counts(db)
        before_hash = face_embedding_hash(db)
        if before_hash != EXPECTED_FACE_HASH:
            raise RuntimeError(
                f"Face embedding hash mismatch before setup: expected {EXPECTED_FACE_HASH}, got {before_hash}"
            )
        department, mca, mtech = resolve_departments(db)
        before_mca = department_counts(db, department.id)
        years = resolve_years(db, mtech)
        check_capacity(db, department, mtech, years)

        print(f"Before global row counts: {before_counts}")
        print(f"Before face_embedding SHA-256: {before_hash}")
        print(f"MCA counts before cleanup: {before_mca}")
        print("Capacity check: PASS (faculty <= 15 and academic years <= 30)")

        cleanup_messages = clean_mca_accounts(db)
        faculties = ensure_faculty(db, department, credentials)
        ensure_labs(db, department)
        ensure_subjects(db, years, faculties)
        ensure_students(db, department, years, credentials)

        generation_results = {}
        for year_name, year in years.items():
            existing_entries = (
                db.query(TimetableEntry)
                .filter(TimetableEntry.academic_year_id == year.id)
                .count()
            )
            if existing_entries:
                generation_results[year_name] = {
                    "placed_count": existing_entries,
                    "unscheduled": [],
                    "feasibility_warnings": [],
                    "skipped": "existing timetable entries preserved",
                }
            else:
                generation_results[year_name] = generate_timetable(db, year.id)

        db.flush()
        after_counts = table_counts(db)
        after_hash = face_embedding_hash(db)
        if after_hash != before_hash:
            raise RuntimeError(
                f"Face embedding hash changed during setup: before {before_hash}, after {after_hash}"
            )
        after_mca = department_counts(db, department.id)
        db.commit()
        outer_transaction.commit()

        print(f"After global row counts: {after_counts}")
        print(f"After face_embedding SHA-256: {after_hash}")
        print(f"MCA counts after cleanup: {after_mca}")
        for message in cleanup_messages:
            print(message)
        print("MTech timetable generation:")
        for year_name, result in generation_results.items():
            print(f"  {year_name}: {result}")
        print("New credentials (shown once):")
        for username, password in credentials:
            print(f"  {username}: {password}")
        print("Setup transaction: COMMITTED")
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
