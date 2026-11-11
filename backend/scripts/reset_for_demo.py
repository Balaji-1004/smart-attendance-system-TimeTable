import os
import secrets
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from app.core.security import hash_password
from app.database.database import SessionLocal, engine
from app.models import (
    AcademicYear,
    Attendance,
    AttendanceSession,
    Department,
    FaceData,
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


FACULTY_DEFINITIONS = [
    {
        "name": "Dr. Ananya Rao",
        "faculty_code": "FAC-001",
        "email": "ananya.rao@demo.invalid",
        "username": "ananya.rao",
    },
    {
        "name": "Prof. Vikram Shah",
        "faculty_code": "FAC-002",
        "email": "vikram.shah@demo.invalid",
        "username": "vikram.shah",
    },
    {
        "name": "Ms. Meera Iyer",
        "faculty_code": "FAC-003",
        "email": "meera.iyer@demo.invalid",
        "username": "meera.iyer",
    },
]

STUDENTS_BY_YEAR = {
    "1st Year": [
        ("Aarav Sharma", "CS1-001"),
        ("Diya Patel", "CS1-002"),
        ("Kabir Nair", "CS1-003"),
        ("Sana Khan", "CS1-004"),
    ],
    "2nd Year": [
        ("Ishaan Mehta", "CS2-001"),
        ("Anaya Reddy", "CS2-002"),
        ("Rohan Das", "CS2-003"),
        ("Tara Menon", "CS2-004"),
    ],
    "3rd Year": [
        ("Arjun Kulkarni", "CS3-001"),
        ("Mira Choudhury", "CS3-002"),
        ("Dev Malhotra", "CS3-003"),
        ("Leela Srinivasan", "CS3-004"),
    ],
}


def make_password():
    return secrets.token_urlsafe(12)


def clear_demo_data(db):
    # Clear the circular optional user/student/faculty references before ordered deletes.
    db.query(Student).update({Student.user_id: None}, synchronize_session=False)
    db.query(User).update(
        {User.faculty_id: None, User.student_id: None},
        synchronize_session=False,
    )
    db.flush()

    models_in_delete_order = [
        Attendance,
        AttendanceSession,
        TimetableEntry,
        FaceData,
        Student,
        Subject,
        FacultyAvailability,
        Lab,
        User,
        Faculty,
        AcademicYear,
    ]
    for model in models_in_delete_order:
        db.query(model).delete(synchronize_session=False)


def reset_for_demo():
    if engine.url.get_backend_name() != "sqlite" or engine.url.database in (None, "", ":memory:"):
        raise RuntimeError(
            f"Expected a persistent SQLite database for the demo reset, got {engine.url}."
        )

    database_path = Path(engine.url.database)
    if not database_path.is_absolute():
        database_path = (BACKEND_DIR / database_path).resolve()

    print(f"Resetting demo data in: {database_path}")
    db = SessionLocal()
    credentials = {}
    timetable_results = []

    try:
        clear_demo_data(db)

        department = (
            db.query(Department)
            .filter(Department.name == "Computer Science")
            .first()
        )
        if department is None:
            department = Department(name="Computer Science")
            db.add(department)
            db.flush()

        programmes = {}
        for name in ("MCA", "MTech"):
            programme = (
                db.query(Programme)
                .filter(Programme.department_id == department.id, Programme.name == name)
                .first()
            )
            if programme is None:
                programme = Programme(department_id=department.id, name=name)
                db.add(programme)
                db.flush()
            programmes[name] = programme

        academic_years = {}
        for name in ("1st Year", "2nd Year"):
            academic_year = AcademicYear(
                department_id=department.id,
                programme_id=programmes["MCA"].id,
                name=name,
            )
            db.add(academic_year)
            db.flush()
            academic_years[name] = academic_year
            db.add(
                AcademicYear(
                    department_id=department.id,
                    programme_id=programmes["MTech"].id,
                    name=name,
                )
            )

        faculty_members = []
        for details in FACULTY_DEFINITIONS:
            faculty = Faculty(
                department_id=department.id,
                name=details["name"],
                faculty_code=details["faculty_code"],
                email=details["email"],
            )
            db.add(faculty)
            db.flush()
            password = make_password()
            db.add(
                User(
                    department_id=department.id,
                    username=details["username"],
                    password_hash=hash_password(password),
                    role=Role.FACULTY,
                    faculty_id=faculty.id,
                )
            )
            faculty_members.append(faculty)
            credentials[details["username"]] = password

        labs = [
            Lab(department_id=department.id, lab_code="LAB-001", name="Computer Lab 1"),
            Lab(department_id=department.id, lab_code="LAB-002", name="Computer Lab 2"),
        ]
        db.add_all(labs)

        hod_username = "demo.hod"
        hod_password = make_password()
        db.add(
            User(
                department_id=department.id,
                username=hod_username,
                password_hash=hash_password(hod_password),
                role=Role.HOD,
                faculty_id=None,
                student_id=None,
            )
        )
        credentials[hod_username] = hod_password

        for year_index, year_name in enumerate(("1st Year", "2nd Year"), start=1):
            year = academic_years[year_name]
            # The primary Java/DBMS instructor covers Java in every year and DBMS
            # in Years 1–2; the AI instructor takes Year 3 DBMS to keep each
            # instructor within the generator's 15-period feasibility limit.
            theory_faculty = faculty_members[0]
            dbms_faculty = faculty_members[0]
            subjects = [
                Subject(
                    academic_year_id=year.id,
                    name="Java",
                    code=f"JAVA-{year_index}",
                    subject_type=SubjectType.THEORY.value,
                    weekly_periods=3,
                    faculty_id=theory_faculty.id,
                ),
                Subject(
                    academic_year_id=year.id,
                    name="AI",
                    code=f"AI-{year_index}",
                    subject_type=SubjectType.THEORY.value,
                    weekly_periods=2,
                    faculty_id=faculty_members[1].id,
                ),
                Subject(
                    academic_year_id=year.id,
                    name="DBMS",
                    code=f"DBMS-{year_index}",
                    subject_type=SubjectType.THEORY.value,
                    weekly_periods=3,
                    faculty_id=dbms_faculty.id,
                ),
                Subject(
                    academic_year_id=year.id,
                    name="Programming Lab",
                    code=f"PLAB-{year_index}",
                    subject_type=SubjectType.LAB.value,
                    weekly_periods=3,
                    faculty_id=faculty_members[2].id,
                ),
            ]
            db.add_all(subjects)

            for student_name, roll_number in STUDENTS_BY_YEAR[year_name]:
                db.add(
                    Student(
                        roll_number=roll_number,
                        name=student_name,
                        email=f"{roll_number.lower()}@students.demo.invalid",
                        academic_year_id=year.id,
                        department_id=department.id,
                        face_registered=False,
                    )
                )

            if year_name == "1st Year":
                demo_student = Student(
                    roll_number="DEMO-001",
                    name="Demo Student",
                    email="demo.student@students.demo.invalid",
                    academic_year_id=year.id,
                    department_id=department.id,
                    face_registered=False,
                )
                db.add(demo_student)
                db.flush()
                student_username = "demo.student"
                student_password = make_password()
                student_user = User(
                    department_id=department.id,
                    username=student_username,
                    password_hash=hash_password(student_password),
                    role=Role.STUDENT,
                    faculty_id=None,
                    student_id=demo_student.id,
                )
                db.add(student_user)
                db.flush()
                demo_student.user_id = student_user.id
                credentials[student_username] = student_password

        db.commit()

        for year_name in ("1st Year", "2nd Year"):
            result = generate_timetable(db, academic_years[year_name].id)
            timetable_results.append((year_name, result))
            print(
                f"\n{year_name} timetable:"
                f"\n  placed_count: {result['placed_count']}"
                f"\n  unscheduled_count: {len(result['unscheduled'])}"
                f"\n  unscheduled: {result['unscheduled']}"
                f"\n  feasibility_warnings: {result['feasibility_warnings']}"
            )

        print("\nDemo login credentials:")
        print(f"  HOD: {hod_username} / {hod_password}")
        print(
            f"  Demo Student: {student_username} / {student_password}"
        )
        print("  Faculty accounts:")
        for details in FACULTY_DEFINITIONS:
            print(f"    {details['name']}: {details['username']} / {credentials[details['username']]}")

        all_years_scheduled = all(not result["unscheduled"] for _, result in timetable_results)
        if all_years_scheduled:
            print(
                "\nSUMMARY: All 3 academic years have generated timetables "
                "with no unscheduled entries."
            )
        else:
            print(
                "\nSUMMARY: WARNING — one or more academic years have "
                "unscheduled timetable entries."
            )
            for year_name, result in timetable_results:
                if result["unscheduled"]:
                    print(f"  {year_name}: {result['unscheduled']}")

        print(
            "\nCreated: 3 academic years, 3 faculty members, 2 labs, "
            "12 regular students, 1 Demo Student, and 12 subjects."
        )
        return 0 if all_years_scheduled else 1
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(reset_for_demo())
