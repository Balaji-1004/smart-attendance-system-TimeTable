import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal
from app.models import AcademicYear, Department, Faculty, Lab, Subject, TimetableEntry
from app.models.enums import SubjectType
from app.services.timetable_generator import generate_timetable


def ensure_year(db, year_name, faculty_code, lab_code):
    dept = db.query(Department).first()
    if dept is None:
        dept = Department(name='Computer Science')
        db.add(dept)
        db.commit(); db.refresh(dept)

    year = db.query(AcademicYear).filter(AcademicYear.name == year_name).first()
    if year is None:
        year = AcademicYear(department_id=dept.id, name=year_name)
        db.add(year)
        db.commit(); db.refresh(year)

    db.query(TimetableEntry).filter(TimetableEntry.academic_year_id == year.id).delete()
    db.query(Subject).filter(Subject.academic_year_id == year.id).delete()

    faculty = db.query(Faculty).filter(Faculty.faculty_code == faculty_code).first()
    if faculty is None:
        faculty = Faculty(name=f'{year_name} Faculty', faculty_code=faculty_code, email=f'{faculty_code.lower()}@example.com')
        db.add(faculty)
        db.commit(); db.refresh(faculty)

    lab = db.query(Lab).filter(Lab.lab_code == lab_code).first()
    if lab is None:
        lab = Lab(lab_code=lab_code, name=lab_code)
        db.add(lab)
        db.commit(); db.refresh(lab)

    for subject in [
        Subject(academic_year_id=year.id, name='Theory 1', code=f'{year_name}-T1', subject_type=SubjectType.THEORY.value, weekly_periods=3, faculty_id=faculty.id),
        Subject(academic_year_id=year.id, name='Theory 2', code=f'{year_name}-T2', subject_type=SubjectType.THEORY.value, weekly_periods=2, faculty_id=faculty.id),
        Subject(academic_year_id=year.id, name='Lab 1', code=f'{year_name}-L1', subject_type=SubjectType.LAB.value, weekly_periods=3, faculty_id=faculty.id),
        Subject(academic_year_id=year.id, name='Lab 2', code=f'{year_name}-L2', subject_type=SubjectType.LAB.value, weekly_periods=3, faculty_id=faculty.id),
    ]:
        db.add(subject)
    db.commit()
    return year.id


def ensure_other_year(db):
    dept = db.query(Department).first()
    if dept is None:
        dept = Department(name='Other Dept')
        db.add(dept)
        db.commit(); db.refresh(dept)

    year_name = 'Other Year 6c'
    year = db.query(AcademicYear).filter(AcademicYear.name == year_name).first()
    if year is None:
        year = AcademicYear(department_id=dept.id, name=year_name)
        db.add(year)
        db.commit(); db.refresh(year)

    db.query(TimetableEntry).filter(TimetableEntry.academic_year_id == year.id).delete()
    db.query(Subject).filter(Subject.academic_year_id == year.id).delete()

    faculty = db.query(Faculty).filter(Faculty.faculty_code == 'FAC-OTHER-6C').first()
    if faculty is None:
        faculty = Faculty(name='Other Faculty 6c', faculty_code='FAC-OTHER-6C', email='other6c@example.com')
        db.add(faculty)
        db.commit(); db.refresh(faculty)

    lab = db.query(Lab).filter(Lab.lab_code == 'LAB-OTHER-6C').first()
    if lab is None:
        lab = Lab(lab_code='LAB-OTHER-6C', name='Other Lab 6c')
        db.add(lab)
        db.commit(); db.refresh(lab)

    subject = Subject(academic_year_id=year.id, name='Other Lab', code='OTHER-L1-6C', subject_type=SubjectType.LAB.value, weekly_periods=3, faculty_id=faculty.id)
    db.add(subject)
    db.commit()
    return year.id


def main():
    db = SessionLocal()
    try:
        year1_id = ensure_year(db, 'Generator Run Year', 'FAC-GEN-RUN', 'LAB-GEN-01')
        year2_id = ensure_other_year(db)

        first_count = db.query(TimetableEntry).count()
        print(f'Initial timetable entries total: {first_count}')

        first_result = generate_timetable(db, year1_id)
        print('FIRST GENERATION RESULT')
        print(first_result)

        year1_rows_after_first = db.query(TimetableEntry).filter(TimetableEntry.academic_year_id == year1_id).count()
        year2_rows_after_first = db.query(TimetableEntry).filter(TimetableEntry.academic_year_id == year2_id).count()
        print(f'After first generation: year1 rows={year1_rows_after_first}, year2 rows={year2_rows_after_first}')

        second_result = generate_timetable(db, year1_id)
        print('SECOND GENERATION RESULT')
        print(second_result)

        year1_rows_after_second = db.query(TimetableEntry).filter(TimetableEntry.academic_year_id == year1_id).count()
        year2_rows_after_second = db.query(TimetableEntry).filter(TimetableEntry.academic_year_id == year2_id).count()
        print(f'After second generation: year1 rows={year1_rows_after_second}, year2 rows={year2_rows_after_second}')
        print(f'First/second count consistent: {year1_rows_after_second == first_result["placed_count"]}')
        print(f'No duplication: {year1_rows_after_second == year1_rows_after_first}')
        print(f'Other year untouched: {year2_rows_after_second == year2_rows_after_first}')
    finally:
        db.close()


if __name__ == '__main__':
    main()
