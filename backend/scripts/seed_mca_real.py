import hashlib
import re
import secrets
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.database import engine
from app.models import AcademicYear, FaceData, Faculty, Programme, Subject, User
from app.models.enums import SubjectType
from app.models.user import Role
from app.services.timetable_generator import generate_timetable


SUBJECTS = (
    ("1st Year", "CSCA 421", "Computer Networks", "THEORY", 3, "Dr T Chithralekha"),
    ("1st Year", "CSCA 422", "Operating Systems", "THEORY", 3, "Dr Rajpriya Darshini"),
    ("1st Year", "CSCA 423", "Communication Skills", "THEORY", 3, "Dr G Krishnapriya"),
    ("1st Year", "CSCA 424", "Computer Networks Lab", "LAB", 3, "Dr T Chithralekha"),
    ("1st Year", "CSCA 425", "Operating Systems Lab", "LAB", 3, "Mr Seenivasan R P"),
    ("1st Year", "CSEL 448", "Ethical Hacking", "THEORY", 3, "Dr Sukhvinder Singh"),
    ("1st Year", "CSEL 581", "Introduction to AI and Expert Systems", "THEORY", 3, "Dr SL Jayalakshmi"),
    ("2nd Year", "CSCA 432", "Management Concepts and Strategies", "THEORY", 3, "Dr G Krishnapriya"),
    ("2nd Year", "CSCA 511", "Software Engineering", "THEORY", 3, "Mr Seenivasan R P"),
    ("2nd Year", "CSCA 512", "Internet and Web Technologies", "THEORY", 3, "Dr Sukhvinder Singh"),
    ("2nd Year", "MCA_DSE_3", "Software Quality Assurance", "THEORY", 3, "Mr Seenivasan R P"),
    ("2nd Year", "CSCA 514", "Internet and Web Technologies Lab", "LAB", 3, "Dr Sukhvinder Singh"),
)
FACULTY_ORDER = tuple(dict.fromkeys(row[5] for row in SUBJECTS))


def username_for(name):
    return re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")


def face_embedding_hash(db):
    digest = hashlib.sha256()
    rows = db.query(FaceData.face_embedding).order_by(FaceData.student_id).all()
    for (embedding,) in rows:
        if embedding is None:
            raise RuntimeError("A face_data.face_embedding value is NULL.")
        digest.update(bytes(embedding))
    return digest.hexdigest()


def main():
    connection = engine.connect()
    outer_transaction = connection.begin()
    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    credentials = []
    try:
        before_face_hash = face_embedding_hash(db)
        before_face_count = db.query(FaceData).count()
        print(f"Before face_embedding SHA-256: {before_face_hash}")
        print(f"Before face_data row count: {before_face_count}")

        department_id = 1
        department = db.query(Programme).filter(
            Programme.department_id == department_id,
            Programme.name == "MCA",
        ).first()
        if department is None:
            raise RuntimeError("Programme MCA is missing from department 1; run migrate_programmes.py first.")
        years = {
            year.name: year
            for year in db.query(AcademicYear)
            .filter(AcademicYear.programme_id == department.id)
            .all()
        }
        if not {"1st Year", "2nd Year"}.issubset(years):
            raise RuntimeError("MCA must contain 1st Year and 2nd Year before seeding.")

        faculty_by_name = {}
        faculty_period_additions = {}
        year_period_additions = {"1st Year": 0, "2nd Year": 0}
        additions = []
        for year_name, code, name, subject_type, weekly_periods, faculty_name in SUBJECTS:
            year = years[year_name]
            existing = (
                db.query(Subject)
                .filter(Subject.academic_year_id == year.id, Subject.code == code)
                .first()
            )
            if existing is None:
                additions.append((year, code, name, subject_type, weekly_periods, faculty_name))
                faculty_period_additions[faculty_name] = (
                    faculty_period_additions.get(faculty_name, 0) + weekly_periods
                )
                year_period_additions[year_name] += weekly_periods

        existing_faculty_periods = dict(
            db.query(Subject.faculty_id, func.coalesce(func.sum(Subject.weekly_periods), 0))
            .group_by(Subject.faculty_id)
            .all()
        )
        for faculty_name, additional_periods in faculty_period_additions.items():
            faculty_code = f"FAC-CS-{FACULTY_ORDER.index(faculty_name) + 1:02d}"
            faculty = db.query(Faculty).filter(Faculty.faculty_code == faculty_code).first()
            current_periods = existing_faculty_periods.get(faculty.id, 0) if faculty else 0
            if current_periods + additional_periods > 15:
                raise RuntimeError(
                    f"Capacity check failed: {faculty_name} would have "
                    f"{current_periods + additional_periods} weekly periods."
                )
        for year_name, additional_periods in year_period_additions.items():
            existing_periods = (
                db.query(func.coalesce(func.sum(Subject.weekly_periods), 0))
                .filter(Subject.academic_year_id == years[year_name].id)
                .scalar()
                or 0
            )
            if existing_periods + additional_periods > 30:
                raise RuntimeError(
                    f"Capacity check failed: MCA {year_name} would have "
                    f"{existing_periods + additional_periods} weekly periods."
                )
        print(
            "Capacity check: PASS "
            "(faculty <= 15/week, each MCA year <= 30/week)"
        )

        for faculty_name in FACULTY_ORDER:
            faculty_code = f"FAC-CS-{FACULTY_ORDER.index(faculty_name) + 1:02d}"
            email = f"{username_for(faculty_name)}@demo.invalid"
            faculty = db.query(Faculty).filter(Faculty.faculty_code == faculty_code).first()
            if faculty is None:
                faculty = db.query(Faculty).filter(Faculty.email == email).first()
            if faculty is None:
                faculty = Faculty(
                    department_id=department_id,
                    name=faculty_name,
                    faculty_code=faculty_code,
                    email=email,
                )
                db.add(faculty)
                db.flush()
            faculty_by_name[faculty_name] = faculty

            faculty_user = (
                db.query(User)
                .filter(User.faculty_id == faculty.id, User.role == Role.FACULTY)
                .first()
            )
            if faculty_user is None:
                username = username_for(faculty_name)
                if db.query(User.id).filter(User.username == username).first() is not None:
                    raise RuntimeError(
                        f"Cannot create faculty login {username}: username already belongs to another account."
                    )
                password = secrets.token_urlsafe(16)
                db.add(
                    User(
                        username=username,
                        password_hash=hash_password(password),
                        role=Role.FACULTY,
                        faculty_id=faculty.id,
                        student_id=None,
                        department_id=department_id,
                    )
                )
                credentials.append((username, password))

        for year, code, name, subject_type, weekly_periods, faculty_name in additions:
            db.add(
                Subject(
                    academic_year_id=year.id,
                    name=name,
                    code=code,
                    subject_type=SubjectType(subject_type).value,
                    weekly_periods=weekly_periods,
                    faculty_id=faculty_by_name[faculty_name].id,
                )
            )
        db.flush()
        print(f"Subjects inserted: {len(additions)}; already present: {len(SUBJECTS) - len(additions)}")

        for year_name in ("1st Year", "2nd Year"):
            result = generate_timetable(db, years[year_name].id)
            print(
                f"MCA {year_name}: placed_count={result['placed_count']}, "
                f"unscheduled={result['unscheduled']}, "
                f"feasibility_warnings={result['feasibility_warnings']}"
            )

        db.flush()
        after_face_hash = face_embedding_hash(db)
        after_face_count = db.query(FaceData).count()
        print(f"After face_embedding SHA-256: {after_face_hash}")
        print(f"After face_data row count: {after_face_count}")
        if after_face_hash != before_face_hash:
            raise RuntimeError("Face embedding hash changed during MCA seeding.")
        if after_face_count != before_face_count:
            raise RuntimeError("face_data row count changed during MCA seeding.")

        db.commit()
        outer_transaction.commit()
        print("MCA seed transaction: COMMITTED")
        print("Credentials (new faculty users only; printed once):")
        for username, password in credentials:
            print(f"{username}: {password}")
    except Exception:
        db.rollback()
        if outer_transaction.is_active:
            outer_transaction.rollback()
        raise
    finally:
        db.close()
        connection.close()


if __name__ == "__main__":
    main()
