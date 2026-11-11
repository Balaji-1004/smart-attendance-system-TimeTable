import logging
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func

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
)
from app.models.enums import Period, SubjectType, WeekDay
from app.services.timetable_generator import MAX_NODES, generate_timetable, run_generation


def report(label, passed, details=""):
    print(f"{label}: {'PASS' if passed else 'FAIL'}" + (f" - {details}" if details else ""))


def ensure_test_database():
    database_path = Path(engine.url.database)
    if database_path.name != "smart_attendance.test_copy.db":
        raise RuntimeError(
            "Refusing to run: DATABASE_URL must point to backend/smart_attendance.test_copy.db"
        )
    resolved = database_path if database_path.is_absolute() else BACKEND_DIR / database_path
    if resolved.resolve().parent != BACKEND_DIR.resolve():
        raise RuntimeError(f"Refusing to run outside backend: {resolved.resolve()}")


def schedule_rows(db, academic_year_id):
    rows = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.academic_year_id == academic_year_id)
        .order_by(
            TimetableEntry.subject_id,
            TimetableEntry.day,
            TimetableEntry.period,
            TimetableEntry.lab_id,
        )
        .all()
    )
    return [
        (
            row.academic_year_id,
            row.subject_id,
            row.faculty_id,
            row.day.value,
            row.period.value,
            row.lab_id,
        )
        for row in rows
    ]


def required_entry_count(db, academic_year_id):
    subjects = db.query(Subject).filter(Subject.academic_year_id == academic_year_id).all()
    return sum(
        subject.weekly_periods
        if subject.subject_type != SubjectType.LAB.value
        else (subject.weekly_periods // 3) * 3
        for subject in subjects
    )


def uniqueness_violations(db, academic_year_id):
    duplicate_year_slots = (
        db.query(TimetableEntry.day, TimetableEntry.period)
        .filter(TimetableEntry.academic_year_id == academic_year_id)
        .group_by(TimetableEntry.day, TimetableEntry.period)
        .having(func.count(TimetableEntry.id) > 1)
        .count()
    )
    duplicate_faculty_slots = (
        db.query(TimetableEntry.faculty_id, TimetableEntry.day, TimetableEntry.period)
        .filter(TimetableEntry.academic_year_id == academic_year_id)
        .group_by(TimetableEntry.faculty_id, TimetableEntry.day, TimetableEntry.period)
        .having(func.count(TimetableEntry.id) > 1)
        .count()
    )
    duplicate_lab_slots = (
        db.query(TimetableEntry.lab_id, TimetableEntry.day, TimetableEntry.period)
        .filter(
            TimetableEntry.academic_year_id == academic_year_id,
            TimetableEntry.lab_id.isnot(None),
        )
        .group_by(TimetableEntry.lab_id, TimetableEntry.day, TimetableEntry.period)
        .having(func.count(TimetableEntry.id) > 1)
        .count()
    )
    return duplicate_year_slots + duplicate_faculty_slots + duplicate_lab_slots


class GenerationLogCapture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.messages = []

    def emit(self, record):
        if record.name == "app.services.timetable_generator":
            self.messages.append(record.getMessage())


def run_with_log_capture(db, academic_year_id):
    logger = logging.getLogger("app.services.timetable_generator")
    capture = GenerationLogCapture()
    old_level = logger.level
    logger.addHandler(capture)
    logger.setLevel(logging.INFO)
    try:
        result = generate_timetable(db, academic_year_id)
    finally:
        logger.removeHandler(capture)
        logger.setLevel(old_level)
    return result, capture.messages[-1] if capture.messages else "NO GENERATION LOG"


def create_greedy_trap(db):
    department = Department(name="Backtracking Regression Dept")
    db.add(department)
    db.flush()
    programme = Programme(department_id=department.id, name="Regression")
    db.add(programme)
    db.flush()
    year = AcademicYear(
        department_id=department.id,
        programme_id=programme.id,
        name="Backtracking Year",
    )
    db.add(year)
    first_faculty = Faculty(
        department_id=department.id,
        name="Flexible Lab Faculty",
        faculty_code="BT-FAC-01",
        email="bt-fac-01@example.invalid",
    )
    constrained_faculty = Faculty(
        department_id=department.id,
        name="Constrained Lab Faculty",
        faculty_code="BT-FAC-02",
        email="bt-fac-02@example.invalid",
    )
    shared_lab = Lab(
        department_id=department.id,
        lab_code="BT-LAB-01",
        name="Shared Backtracking Lab",
    )
    db.add_all((first_faculty, constrained_faculty, shared_lab))
    db.flush()
    db.add_all(
        (
            Subject(
                academic_year_id=year.id,
                name="Flexible Lab Blocks",
                code="BT-LAB-A",
                subject_type=SubjectType.LAB.value,
                weekly_periods=6,
                faculty_id=first_faculty.id,
            ),
            Subject(
                academic_year_id=year.id,
                name="Constrained Lab Block",
                code="BT-LAB-B",
                subject_type=SubjectType.LAB.value,
                weekly_periods=3,
                faculty_id=constrained_faculty.id,
            ),
        )
    )
    db.flush()
    for day in WeekDay:
        for start_period in (Period.P1, Period.P4):
            block_periods = (
                (Period.P1, Period.P2, Period.P3)
                if start_period == Period.P1
                else (Period.P4, Period.P5, Period.P6)
            )
            if day == WeekDay.MONDAY and start_period == Period.P1:
                continue
            db.add_all(
                FacultyAvailability(
                    faculty_id=constrained_faculty.id,
                    day=day,
                    period=period,
                )
                for period in block_periods
            )
    db.commit()
    return year


def create_impossible_case(db):
    department = Department(name="Backtracking Impossible Dept")
    db.add(department)
    db.flush()
    programme = Programme(department_id=department.id, name="Regression")
    db.add(programme)
    db.flush()
    year = AcademicYear(
        department_id=department.id,
        programme_id=programme.id,
        name="Impossible Year",
    )
    faculty = Faculty(
        department_id=department.id,
        name="Overloaded Faculty",
        faculty_code="BT-FAC-IMP",
        email="bt-fac-imp@example.invalid",
    )
    db.add_all((year, faculty))
    db.flush()
    db.add(
        Subject(
            academic_year_id=year.id,
            name="Unavailable Faculty Requirement",
            code="BT-THEORY-UNAVAILABLE",
            subject_type=SubjectType.THEORY.value,
            weekly_periods=3,
            faculty_id=faculty.id,
        )
    )
    db.add_all(
        FacultyAvailability(faculty_id=faculty.id, day=day, period=period)
        for day in WeekDay
        for period in Period
    )
    db.commit()
    return year


def main():
    ensure_test_database()
    db = SessionLocal()
    failures = 0
    try:
        programmes = {
            programme.name: programme.id
            for programme in db.query(Programme)
            .filter(Programme.name.in_(("MCA", "MTech")))
            .all()
        }
        years = (
            db.query(AcademicYear)
            .filter(AcademicYear.programme_id.in_(programmes.values()))
            .order_by(AcademicYear.programme_id, AcademicYear.id)
            .all()
        )
        target_year_count = sum(1 for year in years if year.programme.name == "MCA")
        mtech_year_count = sum(1 for year in years if year.programme.name == "MTech")

        year_results = {}
        expected_year_count = 0
        all_years_ok = target_year_count == 2 and mtech_year_count == 2 and len(years) == 4
        for year in years:
            expected = required_entry_count(db, year.id)
            expected_year_count += expected
            result = generate_timetable(db, year.id)
            actual = db.query(TimetableEntry).filter(
                TimetableEntry.academic_year_id == year.id
            ).count()
            violations = uniqueness_violations(db, year.id)
            year_results[year.id] = (result, actual)
            year_ok = result["placed_count"] == expected and not result["unscheduled"] and actual == expected and violations == 0
            all_years_ok = all_years_ok and year_ok
            print(
                f"Year {year.programme.name} {year.name} (id={year.id}, department_id={year.department_id}): "
                f"{'PASS' if year_ok else 'FAIL'} - required={expected}, placed={result['placed_count']}, "
                f"rows={actual}, unscheduled={len(result['unscheduled'])}, uniqueness_violations={violations}"
            )
        report(
            "a. All MCA/MTech academic years fully schedule",
            all_years_ok,
            f"MCA years={target_year_count}, MTech years={mtech_year_count}, expected total entries={expected_year_count}",
        )
        failures += not all_years_ok

        first_mca_year = next(
            (year for year in years if year.programme.name == "MCA"),
            None,
        )
        determinism_ok = first_mca_year is not None
        rebuild_ok = first_mca_year is not None
        if first_mca_year is not None:
            first_schedule = schedule_rows(db, first_mca_year.id)
            pre_regeneration = {
                year.id: schedule_rows(db, year.id)
                for year in years
            }
            second_result = generate_timetable(db, first_mca_year.id)
            second_schedule = schedule_rows(db, first_mca_year.id)
            other_years_ok = all(
                schedule_rows(db, year.id) == pre_regeneration[year.id]
                for year in years
                if year.id != first_mca_year.id
            )
            target_rows = db.query(TimetableEntry).filter(
                TimetableEntry.academic_year_id == first_mca_year.id
            ).count()
            determinism_ok = (
                determinism_ok
                and second_result["placed_count"] == len(first_schedule)
                and first_schedule == second_schedule
            )
            rebuild_ok = (
                target_rows == second_result["placed_count"]
                and other_years_ok
                and not second_result["unscheduled"]
            )
            report(
                "d. Deterministic regeneration",
                determinism_ok,
                f"year_id={first_mca_year.id}, entries={len(first_schedule)}, "
                f"identical={first_schedule == second_schedule}, nodes/result={second_result['placed_count']}",
            )
            report(
                "e. Regeneration is a clean rebuild; other years untouched",
                rebuild_ok,
                f"target rows={target_rows}, placed_count={second_result['placed_count']}, "
                f"other_years_unchanged={other_years_ok}",
            )
        else:
            report("d. Deterministic regeneration", False, "No MCA academic year found.")
            report("e. Regeneration is a clean rebuild; other years untouched", False, "No MCA academic year found.")
        failures += not determinism_ok
        failures += not rebuild_ok

        trap_year = create_greedy_trap(db)
        greedy_result = run_generation(db, trap_year.id, use_backtracking=False)
        backtracking_result = run_generation(db, trap_year.id, use_backtracking=True)
        greedy_success = len(greedy_result["placed"]) == 6 and len(greedy_result["unscheduled"]) > 0
        backtracking_success = (
            len(backtracking_result["placed"]) == 9
            and not backtracking_result["unscheduled"]
        )
        comparison_ok = greedy_success and backtracking_success
        print(
            "b. Greedy vs backtracking tight case: "
            f"{'PASS' if comparison_ok else 'FAIL'} - greedy placed={len(greedy_result['placed'])}, "
            f"unscheduled={greedy_result['unscheduled']}; backtracking placed={len(backtracking_result['placed'])}, "
            f"unscheduled={backtracking_result['unscheduled']}"
        )
        failures += not comparison_ok

        impossible_year = create_impossible_case(db)
        capture = GenerationLogCapture()
        logger = logging.getLogger("app.services.timetable_generator")
        previous_level = logger.level
        logger.addHandler(capture)
        logger.setLevel(logging.INFO)
        start_time = time.perf_counter()
        try:
            impossible_result = generate_timetable(db, impossible_year.id)
        finally:
            elapsed = time.perf_counter() - start_time
            logger.removeHandler(capture)
            logger.setLevel(previous_level)
        impossible_log = capture.messages[-1] if capture.messages else "NO GENERATION LOG"
        nodes = int(impossible_log.split("nodes=")[1].split()[0]) if "nodes=" in impossible_log else -1
        impossible_ok = (
            nodes > 0
            and len(impossible_result["unscheduled"]) > 0
            and impossible_result["placed_count"] < 3
        )
        report(
            "c. Impossible fully unavailable requirement terminates with shortfall",
            impossible_ok,
            f"required=3, placed={impossible_result['placed_count']}, unscheduled={len(impossible_result['unscheduled'])}, "
            f"nodes={nodes}, max_nodes={MAX_NODES}, elapsed_seconds={elapsed:.3f}, "
            f"reason={impossible_result['unscheduled'][0]['reason'] if impossible_result['unscheduled'] else 'none'}",
        )
        failures += not impossible_ok
        db.rollback()
    finally:
        db.close()
    print(f"OVERALL: {'PASS' if failures == 0 else 'FAIL'} ({5 - failures}/5 checks)")
    return failures == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
