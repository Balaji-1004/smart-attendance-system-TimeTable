import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal
from app.models import AcademicYear, Department, Faculty, Subject
from app.models.enums import SubjectType
from app.services.timetable_generator import load_blocks_for_year


def ensure_test_data(db):
    dept = db.query(Department).first()
    if dept is None:
        dept = Department(name='Computer Science')
        db.add(dept)
        db.commit()
        db.refresh(dept)

    year = db.query(AcademicYear).filter(AcademicYear.name == 'Generator Test Year').first()
    if year is None:
        year = AcademicYear(department_id=dept.id, name='Generator Test Year')
        db.add(year)
        db.commit()
        db.refresh(year)

    faculty = db.query(Faculty).filter(Faculty.faculty_code == 'FAC-GEN-01').first()
    if faculty is None:
        faculty = Faculty(name='Generator Faculty', faculty_code='FAC-GEN-01', email='genfaculty@example.com')
        db.add(faculty)
        db.commit()
        db.refresh(faculty)

    existing_codes = {row.code for row in db.query(Subject).filter(Subject.academic_year_id == year.id).all()}
    subjects = [
        Subject(academic_year_id=year.id, name='Theory A', code='GEN-THEORY-A', subject_type=SubjectType.THEORY.value, weekly_periods=3, faculty_id=faculty.id),
        Subject(academic_year_id=year.id, name='Theory B', code='GEN-THEORY-B', subject_type=SubjectType.THEORY.value, weekly_periods=2, faculty_id=faculty.id),
        Subject(academic_year_id=year.id, name='Lab A', code='GEN-LAB-A', subject_type=SubjectType.LAB.value, weekly_periods=3, faculty_id=faculty.id),
        Subject(academic_year_id=year.id, name='Lab B', code='GEN-LAB-B', subject_type=SubjectType.LAB.value, weekly_periods=4, faculty_id=faculty.id),
    ]

    for subject in subjects:
        if subject.code not in existing_codes:
            db.add(subject)

    db.commit()
    return year.id, faculty.id


def main():
    db = SessionLocal()
    try:
        year_id, faculty_id = ensure_test_data(db)
        result = load_blocks_for_year(db, year_id)

        lab_blocks = result['lab_blocks']
        theory_blocks = result['theory_blocks']
        warnings = result['warnings']

        print(f'lab_blocks created: {len(lab_blocks)}')
        for block in lab_blocks:
            print(f'  - {block}')

        print(f'theory_blocks created: {len(theory_blocks)}')
        for block in theory_blocks:
            print(f'  - {block}')

        print(f'warnings: {warnings}')

        expected_theory_total = 3 + 2
        expected_lab_total = 1 + 1
        if len(theory_blocks) != expected_theory_total:
            raise AssertionError(f'Expected {expected_theory_total} theory blocks, got {len(theory_blocks)}')
        if len(lab_blocks) != expected_lab_total:
            raise AssertionError(f'Expected {expected_lab_total} lab blocks, got {len(lab_blocks)}')
        if not warnings:
            raise AssertionError('Expected a warning for the bad lab subject with weekly_periods=4')

        print('Counts match expectations: PASS')
    finally:
        db.close()


if __name__ == '__main__':
    main()
