import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.database import SessionLocal
from app.models import AcademicYear, Department, Faculty, FacultyAvailability, Lab, Subject, User
from app.models.enums import Period, SubjectType, WeekDay
from app.models.user import Role
from app.services.feasibility_checker import (
    check_faculty_feasibility,
    check_lab_feasibility,
    check_year_feasibility,
    run_full_feasibility_check,
)
from app.services.timetable_validator import (
    check_faculty_availability,
    check_faculty_clash,
    check_faculty_daily_limit,
    check_faculty_weekly_limit,
    check_lab_clash,
    check_lab_concurrency,
    check_lab_room_consistency,
    check_year_clash,
    get_lab_block_periods,
    validate_lab_block,
    validate_single_entry,
)


def seed_minimal_data():
    db = SessionLocal()
    try:
        dept = db.query(Department).first()
        if dept is None:
            dept = Department(name='Computer Science')
            db.add(dept)
            db.commit()
            db.refresh(dept)

        ay = db.query(AcademicYear).first()
        if ay is None:
            ay = AcademicYear(department_id=dept.id, name='1st Year')
            db.add(ay)
            db.commit()
            db.refresh(ay)

        faculty = db.query(Faculty).filter(Faculty.faculty_code == 'FAC-TEST-1').first()
        if faculty is None:
            faculty = Faculty(name='Test Faculty', faculty_code='FAC-TEST-1', email='test1@example.com')
            db.add(faculty)
            db.commit()
            db.refresh(faculty)

        if db.query(User).filter(User.username == 'validator_faculty').first() is None:
            db.add(User(username='validator_faculty', password_hash='hash', role=Role.FACULTY, faculty_id=faculty.id, student_id=None))
            db.commit()

        lab = db.query(Lab).filter(Lab.lab_code == 'LAB-TEST-1').first()
        if lab is None:
            lab = Lab(lab_code='LAB-TEST-1', name='Test Lab')
            db.add(lab)
            db.commit()
            db.refresh(lab)

        subject = db.query(Subject).filter(Subject.code == 'SUB-TEST-1').first()
        if subject is None:
            subject = Subject(
                academic_year_id=ay.id,
                name='Test Theory',
                code='SUB-TEST-1',
                subject_type=SubjectType.THEORY.value,
                weekly_periods=4,
                faculty_id=faculty.id,
            )
            db.add(subject)
            db.commit()
            db.refresh(subject)

        return {
            'year_id': ay.id,
            'faculty_id': faculty.id,
            'lab_id': lab.id,
            'subject_id': subject.id,
        }
    finally:
        db.close()


def print_result(label, ok, detail=None):
    status = 'PASS' if ok else 'FAIL'
    if detail is None:
        print(f'{label}: {status}')
    else:
        print(f'{label}: {status} -> {detail}')


def demo():
    setup = seed_minimal_data()
    db = SessionLocal()
    try:
        year_id = setup['year_id']
        faculty_id = setup['faculty_id']
        lab_id = setup['lab_id']
        subject_id = setup['subject_id']

        # 5a checks
        ok, reason = check_year_clash(db, year_id, WeekDay.MONDAY, Period.P1)
        print_result('year clash valid', ok is True, reason)
        ok, reason = check_year_clash(db, year_id, WeekDay.MONDAY, Period.P1, pending_entries=[{'academic_year_id': year_id, 'day': WeekDay.MONDAY, 'period': Period.P1, 'faculty_id': faculty_id, 'lab_id': None, 'id': 9999}])
        print_result('year clash invalid with pending entry', ok is False, reason)

        ok, reason = check_faculty_clash(db, faculty_id, WeekDay.TUESDAY, Period.P3)
        print_result('faculty clash valid', ok is True, reason)
        ok, reason = check_faculty_clash(db, faculty_id, WeekDay.MONDAY, Period.P1, pending_entries=[{'faculty_id': faculty_id, 'day': WeekDay.MONDAY, 'period': Period.P1, 'academic_year_id': year_id, 'lab_id': None, 'id': 1000}])
        print_result('faculty clash invalid with pending entry', ok is False, reason)

        ok, reason = check_lab_clash(db, lab_id, WeekDay.WEDNESDAY, Period.P4)
        print_result('lab clash valid', ok is True, reason)
        ok, reason = check_lab_clash(db, lab_id, WeekDay.WEDNESDAY, Period.P4, pending_entries=[{'lab_id': lab_id, 'day': WeekDay.WEDNESDAY, 'period': Period.P4, 'faculty_id': faculty_id, 'academic_year_id': year_id, 'id': 2000}])
        print_result('lab clash invalid with pending entry', ok is False, reason)

        ok, reason = check_faculty_daily_limit(db, faculty_id, WeekDay.FRIDAY)
        print_result('daily limit valid', ok is True, reason)
        ok, reason = check_faculty_daily_limit(db, faculty_id, WeekDay.MONDAY, pending_entries=[{'faculty_id': faculty_id, 'day': WeekDay.MONDAY, 'id': 3000}, {'faculty_id': faculty_id, 'day': WeekDay.MONDAY, 'id': 3001}, {'faculty_id': faculty_id, 'day': WeekDay.MONDAY, 'id': 3002}, {'faculty_id': faculty_id, 'day': WeekDay.MONDAY, 'id': 3003}])
        print_result('daily limit invalid', ok is False, reason)

        ok, reason = check_faculty_weekly_limit(db, faculty_id)
        print_result('weekly limit valid', ok is True, reason)
        ok, reason = check_faculty_weekly_limit(db, faculty_id, pending_entries=[{'faculty_id': faculty_id, 'id': 4000} for _ in range(16)])
        print_result('weekly limit invalid', ok is False, reason)

        existing_availability = db.query(FacultyAvailability).filter(FacultyAvailability.faculty_id == faculty_id, FacultyAvailability.day == WeekDay.FRIDAY, FacultyAvailability.period == Period.P5).first()
        if existing_availability:
            db.delete(existing_availability)
            db.commit()
        ok, reason = check_faculty_availability(db, faculty_id, WeekDay.FRIDAY, Period.P5)
        print_result('faculty availability valid', ok is True, reason)
        db.add(FacultyAvailability(faculty_id=faculty_id, day=WeekDay.FRIDAY, period=Period.P5))
        db.commit()
        ok, reason = check_faculty_availability(db, faculty_id, WeekDay.FRIDAY, Period.P5)
        print_result('faculty availability invalid', ok is False, reason)

        ok, reason = check_lab_room_consistency('THEORY', lab_id)
        print_result('lab room consistency invalid theory-with-lab', ok is False, reason)
        ok, reason = check_lab_room_consistency('LAB', None)
        print_result('lab room consistency invalid lab-without-room', ok is False, reason)
        ok, reason = check_lab_room_consistency('THEORY', None)
        print_result('lab room consistency valid theory-without-room', ok is True, reason)
        ok, reason = check_lab_room_consistency('LAB', lab_id)
        print_result('lab room consistency valid lab-with-room', ok is True, reason)

        ok, reasons = validate_single_entry(
            db,
            academic_year_id=year_id,
            subject_id=subject_id,
            faculty_id=faculty_id,
            day=WeekDay.FRIDAY,
            period=Period.P6,
            lab_id=None,
            subject_type='THEORY',
            pending_entries=[],
        )
        print_result('validate_single_entry pass case', ok is True, reasons)

        ok, reasons = validate_single_entry(
            db,
            academic_year_id=year_id,
            subject_id=subject_id,
            faculty_id=faculty_id,
            day=WeekDay.THURSDAY,
            period=Period.P1,
            lab_id=None,
            subject_type='THEORY',
            pending_entries=[],
        )
        print_result('validate_single_entry fail case', ok is False, reasons)

        # 5b lab-block and feasibility checks
        print_result('lab block valid start P1', get_lab_block_periods(Period.P1) == [Period.P1, Period.P2, Period.P3])
        print_result('lab block invalid start P2', get_lab_block_periods(Period.P2) is None)
        print_result('lab block valid start P4', get_lab_block_periods(Period.P4) == [Period.P4, Period.P5, Period.P6])

        ok, reason = check_lab_concurrency(db, WeekDay.FRIDAY, Period.P4, 1)
        print_result('lab concurrency valid', ok is True, reason)

        ok, reason = check_lab_concurrency(db, WeekDay.FRIDAY, Period.P4, 1, pending_entries=[{'day': WeekDay.FRIDAY, 'period': Period.P4, 'lab_id': lab_id, 'id': 5000}])
        print_result('lab concurrency invalid', ok is False, reason)

        ok, reasons = validate_lab_block(
            db,
            academic_year_id=year_id,
            subject_id=subject_id,
            faculty_id=faculty_id,
            lab_id=lab_id,
            day=WeekDay.TUESDAY,
            start_period=Period.P1,
            lab_total_count=1,
            pending_entries=[],
        )
        print_result('validate_lab_block pass case', ok is True, reasons)

        ok, reasons = validate_lab_block(
            db,
            academic_year_id=year_id,
            subject_id=subject_id,
            faculty_id=faculty_id,
            lab_id=lab_id,
            day=WeekDay.TUESDAY,
            start_period=Period.P1,
            lab_total_count=1,
            pending_entries=[{'academic_year_id': year_id, 'subject_id': subject_id, 'faculty_id': faculty_id, 'day': WeekDay.TUESDAY, 'period': Period.P1, 'lab_id': lab_id, 'id': 6000}],
        )
        print_result('validate_lab_block fail case', ok is False, reasons)

        # feasibility checks
        # create a year with total weekly periods over 30
        ay_big = db.query(AcademicYear).filter_by(department_id=1, name='Heavy Year').first()
        if ay_big is None:
            ay_big = AcademicYear(department_id=1, name='Heavy Year')
            db.add(ay_big)
            db.commit(); db.refresh(ay_big)
        for idx in range(8):
            code = f'HEAVY{idx}'
            existing = db.query(Subject).filter_by(academic_year_id=ay_big.id, code=code).first()
            if existing is None:
                db.add(Subject(academic_year_id=ay_big.id, name=f'Heavy {idx}', code=code, subject_type=SubjectType.THEORY.value, weekly_periods=5, faculty_id=faculty_id))
        db.commit()
        warnings = check_year_feasibility(db, ay_big.id)
        print_result('year feasibility catches overload', bool(warnings), warnings)

        # faculty across years over 15
        faculty_warnings = check_faculty_feasibility(db, faculty_id)
        print_result('faculty feasibility catches overload', bool(faculty_warnings), faculty_warnings)

        lab_warnings = check_lab_feasibility(db, ay_big.id)
        print_result('lab feasibility result', bool(lab_warnings), lab_warnings)

        full_result = run_full_feasibility_check(db, ay_big.id)
        print_result('full feasibility check returns dict', isinstance(full_result, dict), str(full_result))
    finally:
        db.close()


if __name__ == '__main__':
    demo()
