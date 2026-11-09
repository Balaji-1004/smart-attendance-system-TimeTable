import argparse
import secrets
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import hash_password
from app.database.database import SessionLocal
from app.models import AcademicYear, Department, Faculty, Lab, Student, Subject, User
from app.models.user import Role


def create_department(db, name, hod_username, hod_password=None, years=None, use_existing=False):
    if use_existing:
        department = db.query(Department).filter(Department.name == name).first()
        if department is None:
            raise ValueError(f"Department '{name}' does not exist.")

        faculty_ids = db.query(Faculty.id).filter(Faculty.department_id == department.id)
        student_ids = db.query(Student.id).filter(Student.department_id == department.id)
        user_count = db.query(User).filter(
            (User.department_id == department.id)
            | (User.faculty_id.in_(faculty_ids))
            | (User.student_id.in_(student_ids))
        ).count()
        existing_counts = {
            "academic years": db.query(AcademicYear).filter(
                AcademicYear.department_id == department.id
            ).count(),
            "users": user_count,
            "students": db.query(Student).filter(
                Student.department_id == department.id
            ).count(),
            "faculty": db.query(Faculty).filter(
                Faculty.department_id == department.id
            ).count(),
            "labs": db.query(Lab).filter(Lab.department_id == department.id).count(),
            "subjects": db.query(Subject)
            .join(AcademicYear, AcademicYear.id == Subject.academic_year_id)
            .filter(AcademicYear.department_id == department.id)
            .count(),
        }
        populated = [f"{label}: {count}" for label, count in existing_counts.items() if count]
        if populated:
            raise ValueError(
                f"Department '{name}' is not empty (" + ", ".join(populated) + ")."
            )
        if db.query(User).filter(User.username == hod_username).first() is not None:
            raise ValueError(f"Username '{hod_username}' already exists.")

        password = hod_password or secrets.token_urlsafe(16)
        year_names = years or ["1st Year", "2nd Year", "3rd Year"]
        try:
            db.add_all(
                AcademicYear(department_id=department.id, name=year_name)
                for year_name in year_names
            )
            db.add(
                User(
                    username=hod_username,
                    password_hash=hash_password(password),
                    role=Role.HOD,
                    department_id=department.id,
                )
            )
            db.commit()
            db.refresh(department)
            return department, password if hod_password is None else None
        except Exception:
            db.rollback()
            raise

    if db.query(Department).filter(Department.name == name).first() is not None:
        raise ValueError(f"Department '{name}' already exists.")
    if db.query(User).filter(User.username == hod_username).first() is not None:
        raise ValueError(f"Username '{hod_username}' already exists.")

    password = hod_password or secrets.token_urlsafe(16)
    year_names = years or ["1st Year", "2nd Year", "3rd Year"]
    department = Department(name=name)

    try:
        db.add(department)
        db.flush()
        db.add_all(
            AcademicYear(department_id=department.id, name=year_name)
            for year_name in year_names
        )
        db.add(
            User(
                username=hod_username,
                password_hash=hash_password(password),
                role=Role.HOD,
                department_id=department.id,
            )
        )
        db.commit()
        db.refresh(department)
        return department, password if hod_password is None else None
    except Exception:
        db.rollback()
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--hod-username", required=True)
    parser.add_argument("--hod-password")
    parser.add_argument(
        "--years",
        default="1st Year,2nd Year,3rd Year",
    )
    parser.add_argument(
        "--use-existing",
        action="store_true",
        help="Add years and an HOD to an existing empty department.",
    )
    args = parser.parse_args()
    year_names = [name.strip() for name in args.years.split(",") if name.strip()]

    db = SessionLocal()
    try:
        _, generated_password = create_department(
            db,
            args.name,
            args.hod_username,
            args.hod_password,
            year_names,
            use_existing=args.use_existing,
        )
        if generated_password is not None:
            print(generated_password)
    except ValueError as exc:
        parser.error(str(exc))
    finally:
        db.close()


if __name__ == "__main__":
    main()
