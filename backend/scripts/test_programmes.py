import hashlib
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import create_access_token, hash_password
from app.database.database import SessionLocal, engine
from app.main import app
from app.models import (
    AcademicYear,
    Department,
    Faculty,
    FacultyFaceData,
    FaceData,
    Programme,
    Student,
    User,
)
from app.models.user import Role


def report(label, passed, details=""):
    print(f"{label}: {'PASS' if passed else 'FAIL'}" + (f" - {details}" if details else ""))
    return bool(passed)


def ensure_test_database():
    database_path = Path(engine.url.database)
    if database_path.name != "smart_attendance.test_copy.db":
        raise RuntimeError(
            "Refusing to run: DATABASE_URL must point to backend/smart_attendance.test_copy.db"
        )
    resolved = database_path if database_path.is_absolute() else BACKEND_DIR / database_path
    if resolved.resolve().parent != BACKEND_DIR.resolve():
        raise RuntimeError(f"Refusing to run outside backend: {resolved.resolve()}")


def token_for(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


def embedding_hash(db):
    digest = hashlib.sha256()
    for (embedding,) in db.query(FaceData.face_embedding).order_by(FaceData.student_id).all():
        digest.update(embedding or b"")
    return digest.hexdigest()


def main():
    ensure_test_database()
    db = SessionLocal()
    checks = []
    try:
        department = db.query(Department).filter(Department.id == 1).first()
        if department is None:
            raise RuntimeError("Department id 1 is missing.")
        hod = db.query(User).filter(User.username == "demo.hod").first()
        faculty_user = (
            db.query(User)
            .filter(User.role == Role.FACULTY, User.department_id == department.id)
            .order_by(User.id)
            .first()
        )
        student = db.query(Student).filter(Student.department_id == department.id).order_by(Student.id).first()
        student_user = (
            db.query(User)
            .filter(User.role == Role.STUDENT, User.department_id == department.id)
            .order_by(User.id)
            .first()
        )
        if hod is None or faculty_user is None or student is None or student_user is None:
            raise RuntimeError("The migrated department and demo accounts are incomplete.")

        other_department = Department(name="Programme Isolation Dept")
        db.add(other_department)
        db.flush()
        other_programme = Programme(department_id=other_department.id, name="Other Programme")
        other_programme_two = Programme(
            department_id=other_department.id,
            name="Other Programme Two",
        )
        other_year = AcademicYear(
            department_id=other_department.id,
            programme=other_programme,
            name="1st Year",
        )
        other_hod = User(
            username="programme.other.hod",
            password_hash=hash_password("test-password"),
            role=Role.HOD,
            department_id=other_department.id,
        )
        other_faculty = Faculty(
            department_id=other_department.id,
            name="Other Department Faculty",
            faculty_code="PROG-OTHER-FAC",
            email="prog-other-faculty@example.invalid",
        )
        db.add_all((other_programme, other_programme_two, other_year, other_hod, other_faculty))
        db.flush()
        other_faculty_user = User(
            username="programme.other.faculty",
            password_hash=hash_password("test-password"),
            role=Role.FACULTY,
            department_id=other_department.id,
            faculty_id=other_faculty.id,
        )
        other_student = Student(
            roll_number="PROG-OTHER-001",
            name="Other Department Student",
            email="prog-other-student@example.invalid",
            academic_year_id=other_year.id,
            department_id=other_department.id,
        )
        db.add(other_student)
        db.flush()
        other_student_user = User(
            username="programme.other.student",
            password_hash=hash_password("test-password"),
            role=Role.STUDENT,
            department_id=other_department.id,
            student_id=other_student.id,
        )
        db.add_all((other_faculty_user, other_student_user))
        db.commit()
        before_face_hash = embedding_hash(db)
        before_face_rows = db.query(FaceData).count()
        other_faculty_id = other_faculty.id
        other_department_id = other_department.id
        other_programme_id = other_programme.id
        other_programme_two_id = other_programme_two.id
        hod_headers = token_for(hod)
        faculty_headers = token_for(faculty_user)
        student_headers = token_for(student_user)
        other_hod_headers = token_for(other_hod)

        with TestClient(app) as client:
            created = client.post("/programmes", json={"name": "Programme Test"}, headers=hod_headers)
            created_id = created.json().get("id") if created.status_code == 200 else None
            checks.append(report("HOD creates programme", created.status_code == 200, f"status={created.status_code}"))

            listing = client.get("/programmes", headers=hod_headers)
            checks.append(
                report(
                    "Programme list is department-scoped",
                    listing.status_code == 200
                    and all(item["department_id"] == department.id for item in listing.json())
                    and not {other_programme_id, other_programme_two_id}
                    .intersection(item["id"] for item in listing.json()),
                    f"status={listing.status_code}, rows={len(listing.json()) if listing.status_code == 200 else 0}",
                )
            )
            faculty_listing = client.get("/programmes", headers=faculty_headers)
            checks.append(
                report(
                    "Faculty can list own department programmes",
                    faculty_listing.status_code == 200
                    and all(item["department_id"] == department.id for item in faculty_listing.json()),
                    f"status={faculty_listing.status_code}",
                )
            )
            student_listing = client.get("/programmes", headers=student_headers)
            checks.append(report("Student cannot list programmes", student_listing.status_code == 403, f"status={student_listing.status_code}"))
            faculty_create = client.post("/programmes", json={"name": "Forbidden"}, headers=faculty_headers)
            checks.append(report("Faculty cannot create programme", faculty_create.status_code == 403, f"status={faculty_create.status_code}"))

            updated = client.put(
                f"/programmes/{created_id}",
                json={"name": "Programme Test Updated"},
                headers=hod_headers,
            )
            checks.append(
                report(
                    "HOD updates programme",
                    updated.status_code == 200 and updated.json().get("name") == "Programme Test Updated",
                    f"status={updated.status_code}",
                )
            )

            year_one = client.post(
                "/academic-years",
                json={"programme_id": created_id, "name": "1st Year"},
                headers=hod_headers,
            )
            mca_programme = next(
                row for row in listing.json() if row["name"] == "MCA"
            )
            year_same_name = client.post(
                "/academic-years",
                json={"programme_id": mca_programme["id"], "name": "1st Year"},
                headers=hod_headers,
            )
            year_mtech_same_name = client.post(
                "/academic-years",
                json={"programme_id": other_programme_two_id, "name": "1st Year"},
                headers=other_hod_headers,
            )
            checks.append(
                report(
                    "Academic year requires same-department programme; year names repeat across programmes",
                    year_one.status_code == 200
                    and year_one.json().get("programme_name") == "Programme Test Updated"
                    and year_same_name.status_code == 400
                    and year_mtech_same_name.status_code == 200,
                    f"created={year_one.status_code}, duplicate-in-programme={year_same_name.status_code}, "
                    f"same-name-other-programme={year_mtech_same_name.status_code}",
                )
            )
            cross_programme_year = client.post(
                "/academic-years",
                json={"programme_id": other_programme_id, "name": "Cross Department Year"},
                headers=hod_headers,
            )
            checks.append(
                report(
                    "Academic year rejects another department's programme",
                    cross_programme_year.status_code == 404,
                    f"status={cross_programme_year.status_code}",
                )
            )
            filtered_years = client.get(
                f"/academic-years?programme_id={created_id}",
                headers=hod_headers,
            )
            checks.append(
                report(
                    "Academic year list filters by programme",
                    filtered_years.status_code == 200
                    and all(row["programme_id"] == created_id for row in filtered_years.json()),
                    f"status={filtered_years.status_code}, rows={len(filtered_years.json()) if filtered_years.status_code == 200 else 0}",
                )
            )
            blocked_delete = client.delete(f"/programmes/{created_id}", headers=hod_headers)
            checks.append(
                report(
                    "Programme with academic years cannot be deleted",
                    blocked_delete.status_code == 400,
                    f"status={blocked_delete.status_code}",
                )
            )
            empty_programme = client.post("/programmes", json={"name": "Delete Me"}, headers=hod_headers)
            delete_id = empty_programme.json().get("id") if empty_programme.status_code == 200 else -1
            deleted = client.delete(f"/programmes/{delete_id}", headers=hod_headers)
            checks.append(report("Empty programme can be deleted", deleted.status_code == 204, f"status={deleted.status_code}"))

            faculty_id = faculty_user.faculty_id
            cross_face = client.post(
                f"/faculty/{other_faculty_id}/face-registration",
                files={"file": ("face.jpg", b"test-image", "image/jpeg")},
                headers=hod_headers,
            )
            checks.append(report("HOD cannot register cross-department faculty face", cross_face.status_code == 404, f"status={cross_face.status_code}"))

            face_module = sys.modules["app.routers.faculty"]
            with patch.object(face_module, "detect_single_face", return_value={"face_count": 1}), patch.object(
                face_module,
                "generate_embedding",
                side_effect=[np.zeros(4096, dtype=np.float32), np.ones(4096, dtype=np.float32)],
            ):
                first_registration = client.post(
                    "/faculty/me/face-registration",
                    files={"file": ("face.jpg", b"test-image", "image/jpeg")},
                    headers=faculty_headers,
                )
                second_registration = client.post(
                    "/faculty/me/face-registration",
                    files={"file": ("face.jpg", b"test-image-2", "image/jpeg")},
                    headers=faculty_headers,
                )
            checks.append(
                report(
                    "Faculty self-registration and re-registration update one row",
                    first_registration.status_code == 200
                    and second_registration.status_code == 200
                    and db.query(FacultyFaceData).filter(FacultyFaceData.faculty_id == faculty_id).count() == 1,
                    f"first={first_registration.status_code}, second={second_registration.status_code}, "
                    f"rows={db.query(FacultyFaceData).filter(FacultyFaceData.faculty_id == faculty_id).count()}",
                )
            )
            status_response = client.get(
                f"/faculty/{faculty_id}/face-registration-status",
                headers=hod_headers,
            )
            checks.append(
                report(
                    "HOD reads faculty face-registration status",
                    status_response.status_code == 200
                    and status_response.json().get("face_registered") is True
                    and status_response.json().get("face_data_exists") is True,
                    f"status={status_response.status_code}",
                )
            )

            with patch.object(face_module, "detect_single_face", return_value={"face_count": 0}):
                no_face = client.post(
                    "/faculty/me/face-registration",
                    files={"file": ("face.jpg", b"test-image", "image/jpeg")},
                    headers=faculty_headers,
                )
            with patch.object(face_module, "detect_single_face", return_value={"face_count": 2}):
                multiple_faces = client.post(
                    "/faculty/me/face-registration",
                    files={"file": ("face.jpg", b"test-image", "image/jpeg")},
                    headers=faculty_headers,
                )
            checks.append(
                report(
                    "Faculty registration rejects zero and multiple faces",
                    no_face.status_code == 400 and multiple_faces.status_code == 400,
                    f"zero={no_face.status_code}, multiple={multiple_faces.status_code}",
                )
            )
            student_face = client.post(
                "/faculty/me/face-registration",
                files={"file": ("face.jpg", b"test-image", "image/jpeg")},
                headers=student_headers,
            )
            checks.append(report("Student cannot use faculty face registration", student_face.status_code == 403, f"status={student_face.status_code}"))

        db.expire_all()
        after_face_hash = embedding_hash(db)
        after_face_rows = db.query(FaceData).count()
        checks.append(
            report(
                "Student face_data unchanged",
                after_face_hash == before_face_hash and after_face_rows == before_face_rows,
                f"hash_unchanged={after_face_hash == before_face_hash}, rows={before_face_rows}->{after_face_rows}",
            )
        )
        print(f"OVERALL: {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)} checks)")
        return all(checks)
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
