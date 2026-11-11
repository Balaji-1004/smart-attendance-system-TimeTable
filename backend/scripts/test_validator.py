import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.database import SessionLocal, engine
from app.models import (
    AcademicYear,
    Department,
    Faculty,
    FacultyAvailability,
    Lab,
    Programme,
    Subject,
    TimetableEntry,
    User,
)
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

FAILURES = 0


def seed_minimal_data():
    database_path = Path(engine.url.database)
    if database_path.name != "smart_attendance.test_copy.db":
        raise RuntimeError(
            "Refusing to run: DATABASE_URL must point to backend/smart_attendance.test_copy.db"
        )
    resolved = database_path if database_path.is_absolute() else PROJECT_ROOT / database_path
    if resolved.resolve().parent != PROJECT_ROOT.resolve():
        raise RuntimeError(f"Refusing to run outside backend: {resolved.resolve()}")

    db = SessionLocal()
    try:
        dept = db.query(Department).first()
        if dept is None:
            dept = Department(name='Computer Science')
            db.add(dept)
            db.commit()
            db.refresh(dept)

        programme = db.query(Programme).filter(
            Programme.department_id == dept.id
        ).order_by(Programme.id).first()
        if programme is None:
            programme = Programme(department_id=dept.id, name="Validator Programme")
            db.add(programme)
            db.commit()
            db.refresh(programme)

        ay = db.query(AcademicYear).first()
        if ay is None:
            ay = AcademicYear(department_id=dept.id, programme_id=programme.id, name='1st Year')
            db.add(ay)
            db.commit()
            db.refresh(ay)

        next_faculty_id = (db.query(Faculty.id).order_by(Faculty.id.desc()).first() or (0,))[0] + 1
        faculty_code = f'FAC-TEST-ISOLATED-{next_faculty_id}'
        faculty = Faculty(
            name='Test Faculty',
            faculty_code=faculty_code,
            email=f'test-validator-{next_faculty_id}@example.com',
            department_id=dept.id,
        )
        db.add(faculty)
        db.commit()
        db.refresh(faculty)

        if db.query(User).filter(User.username == 'validator_faculty').first() is None:
            db.add(User(username='validator_faculty', password_hash='hash', role=Role.FACULTY, faculty_id=faculty.id, student_id=None))
            db.commit()

        lab = db.query(Lab).filter(Lab.lab_code == 'LAB-TEST-1').first()
        if lab is None:
            lab = Lab(department_id=dept.id, lab_code='LAB-TEST-1', name='Test Lab')
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
            'programme_id': programme.id,
            'department_id': dept.id,
            'faculty_id': faculty.id,
            'lab_id': lab.id,
            'subject_id': subject.id,
        }
    finally:
        db.close()


def print_result(label, ok, detail=None):
    global FAILURES
    status = 'PASS' if ok else 'FAIL'
    if not ok:
        FAILURES += 1
    if detail is None:
        print(f'{label}: {status}')
    else:
        print(f'{label}: {status} -> {detail}')


def test_faculty_limit_edges(setup):
    db = SessionLocal()
    try:
        year = AcademicYear(
            department_id=db.query(Department).order_by(Department.id).first().id,
            programme_id=setup["programme_id"],
            name="Limit Regression Year",
        )
        db.add(year)
        db.flush()
        lab_faculty = Faculty(
            department_id=year.department_id,
            name="Limit Regression Lab Faculty",
            faculty_code=f"FAC-LIMIT-LAB-{year.id}",
            email=f"faculty-limit-lab-{year.id}@example.invalid",
        )
        db.add(lab_faculty)
        db.flush()
        subject = Subject(
            academic_year_id=year.id,
            name="Limit Regression Theory",
            code="LIMIT-THEORY",
            subject_type=SubjectType.THEORY.value,
            weekly_periods=1,
            faculty_id=setup["faculty_id"],
        )
        lab_subject = Subject(
            academic_year_id=year.id,
            name="Limit Regression Lab",
            code="LIMIT-LAB-SUBJECT",
            subject_type=SubjectType.LAB.value,
            weekly_periods=3,
            faculty_id=lab_faculty.id,
        )
        lab = Lab(
            department_id=year.department_id,
            lab_code="LIMIT-REGRESSION-LAB",
            name="Limit Regression Lab",
        )
        db.add_all((subject, lab_subject, lab))
        db.flush()

        periods_by_day = {
            WeekDay.MONDAY: (Period.P1, Period.P2),
            WeekDay.TUESDAY: (Period.P1, Period.P2, Period.P3),
            WeekDay.WEDNESDAY: (Period.P1, Period.P2, Period.P3),
            WeekDay.THURSDAY: (Period.P1, Period.P2, Period.P3),
            WeekDay.FRIDAY: (Period.P1, Period.P2, Period.P3),
        }
        entries = [
            TimetableEntry(
                academic_year_id=year.id,
                subject_id=subject.id,
                faculty_id=setup["faculty_id"],
                day=day,
                period=period,
            )
            for day, periods in periods_by_day.items()
            for period in periods
        ]
        db.add_all(entries)
        db.flush()

        third_allowed = check_faculty_daily_limit(
            db, setup["faculty_id"], WeekDay.MONDAY
        )[0]
        print_result("faculty 3rd period allowed", third_allowed, "2 existing + candidate = 3")
        fifteenth_allowed = check_faculty_weekly_limit(db, setup["faculty_id"])[0]
        print_result("faculty 15th weekly period allowed", fifteenth_allowed, "14 existing + candidate = 15")

        monday_third = TimetableEntry(
            academic_year_id=year.id,
            subject_id=subject.id,
            faculty_id=setup["faculty_id"],
            day=WeekDay.MONDAY,
            period=Period.P3,
        )
        db.add(monday_third)
        db.flush()
        fourth_rejected = not check_faculty_daily_limit(
            db, setup["faculty_id"], WeekDay.MONDAY
        )[0]
        print_result("faculty 4th period rejected", fourth_rejected, "3 existing + candidate = 4")

        db.commit()
        sixteenth_rejected = not check_faculty_weekly_limit(
            db, setup["faculty_id"]
        )[0]
        print_result("faculty 16th weekly period rejected", sixteenth_rejected, "15 existing + candidate = 16")

        pending = [
            {
                "id": entry.id,
                "academic_year_id": entry.academic_year_id,
                "subject_id": entry.subject_id,
                "faculty_id": entry.faculty_id,
                "day": entry.day,
                "period": entry.period,
                "lab_id": entry.lab_id,
            }
            for entry in db.query(TimetableEntry).filter(
                TimetableEntry.academic_year_id == year.id
            ).all()
        ]
        move_valid, move_reasons = validate_single_entry(
            db,
            academic_year_id=year.id,
            subject_id=subject.id,
            faculty_id=setup["faculty_id"],
            day=WeekDay.MONDAY,
            period=Period.P4,
            lab_id=None,
            subject_type=SubjectType.THEORY.value,
            pending_entries=pending,
            exclude_entry_id=monday_third.id,
        )
        print_result(
            "moving entry within same day avoids double counting",
            move_valid,
            f"excluded id={monday_third.id}; reasons={move_reasons}",
        )

        unchanged_valid, unchanged_reasons = validate_single_entry(
            db,
            academic_year_id=year.id,
            subject_id=subject.id,
            faculty_id=setup["faculty_id"],
            day=WeekDay.MONDAY,
            period=Period.P3,
            lab_id=None,
            subject_type=SubjectType.THEORY.value,
            pending_entries=pending,
            exclude_entry_id=monday_third.id,
        )
        print_result(
            "unchanged edit passes limits",
            unchanged_valid,
            f"excluded id={monday_third.id}; reasons={unchanged_reasons}",
        )

        lab_ok, lab_reasons = validate_lab_block(
            db,
            academic_year_id=year.id,
            subject_id=lab_subject.id,
            faculty_id=lab_faculty.id,
            lab_id=lab.id,
            day=WeekDay.MONDAY,
            start_period=Period.P4,
            lab_total_count=db.query(Lab).filter(Lab.department_id == year.department_id).count(),
            pending_entries=[],
            department_id=year.department_id,
        )
        print_result(
            "lab block counts three candidate periods",
            lab_ok,
            f"daily=3, weekly=3; reasons={lab_reasons}",
        )
    finally:
        db.close()


def demo():
    setup = seed_minimal_data()
    db = SessionLocal()
    try:
        year_id = setup['year_id']
        faculty_id = setup['faculty_id']
        lab_id = setup['lab_id']
        subject_id = setup['subject_id']

        # 5a checks
        year_slot = next(
            (
                (day, period)
                for day in WeekDay
                for period in Period
                if check_year_clash(db, year_id, day, period)[0]
            ),
            None,
        )
        ok, reason = (
            check_year_clash(db, year_id, *year_slot)
            if year_slot is not None
            else (False, "No free academic-year slot.")
        )
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
        ok, reason = check_faculty_weekly_limit(
            db,
            faculty_id,
            pending_entries=[
                {'faculty_id': faculty_id, 'id': 4000 + index}
                for index in range(16)
            ],
        )
        print_result('weekly limit invalid', ok is False, reason)

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
            pending_entries=[{
                'academic_year_id': year_id,
                'subject_id': subject_id,
                'faculty_id': faculty_id,
                'day': WeekDay.THURSDAY,
                'period': Period.P1,
                'lab_id': None,
                'id': 9000,
            }],
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

        lab_total_count = db.query(Lab).count()
        valid_lab_block = None
        for day in WeekDay:
            for start_period in (Period.P1, Period.P4):
                result = validate_lab_block(
                    db,
                    academic_year_id=year_id,
                    subject_id=subject_id,
                    faculty_id=faculty_id,
                    lab_id=lab_id,
                    day=day,
                    start_period=start_period,
                    lab_total_count=lab_total_count,
                    pending_entries=[],
                )
                if result[0]:
                    valid_lab_block = (day, start_period)
                    break
            if valid_lab_block is not None:
                break
        ok, reasons = (True, []) if valid_lab_block is not None else (False, ["No valid lab block slot found."])
        print_result('validate_lab_block pass case', ok is True, reasons)

        failure_day, failure_start = valid_lab_block or (WeekDay.TUESDAY, Period.P1)
        ok, reasons = validate_lab_block(
            db,
            academic_year_id=year_id,
            subject_id=subject_id,
            faculty_id=faculty_id,
            lab_id=lab_id,
            day=failure_day,
            start_period=failure_start,
            lab_total_count=lab_total_count,
            pending_entries=[{
                'academic_year_id': year_id,
                'subject_id': subject_id,
                'faculty_id': faculty_id,
                'day': failure_day,
                'period': failure_start,
                'lab_id': lab_id,
                'id': 6000,
            }],
        )
        print_result('validate_lab_block fail case', ok is False, reasons)

        # feasibility checks
        # create a year with total weekly periods over 30
        ay_big = db.query(AcademicYear).filter_by(
            programme_id=setup["programme_id"],
            name='Heavy Year',
        ).first()
        if ay_big is None:
            ay_big = AcademicYear(
                department_id=setup["department_id"],
                programme_id=setup["programme_id"],
                name='Heavy Year',
            )
            db.add(ay_big)
            db.commit(); db.refresh(ay_big)
        for idx in range(8):
            code = f'HEAVY{idx}'
            existing = db.query(Subject).filter_by(academic_year_id=ay_big.id, code=code).first()
            if existing is None:
                db.add(Subject(academic_year_id=ay_big.id, name=f'Heavy {idx}', code=code, subject_type=SubjectType.THEORY.value, weekly_periods=5, faculty_id=faculty_id))
        db.commit()
        lab_requirement = db.query(Subject).filter_by(
            academic_year_id=ay_big.id,
            code='HEAVY-LAB-REQUIREMENT',
        ).first()
        if lab_requirement is None:
            db.add(Subject(
                academic_year_id=ay_big.id,
                name='Heavy Lab Requirement',
                code='HEAVY-LAB-REQUIREMENT',
                subject_type=SubjectType.LAB.value,
                weekly_periods=153,
                faculty_id=faculty_id,
            ))
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
    test_faculty_limit_edges(setup)
    print(f"OVERALL: {'FAIL' if FAILURES else 'PASS'} ({FAILURES} failed checks)")
    if FAILURES:
        raise SystemExit(1)


if __name__ == '__main__':
    demo()
