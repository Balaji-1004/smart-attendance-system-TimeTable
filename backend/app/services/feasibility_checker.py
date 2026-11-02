import math

from sqlalchemy import func

from app.models import Faculty, Lab, Subject
from app.models.enums import SubjectType


def check_year_feasibility(db, academic_year_id):
    total_periods = (
        db.query(func.coalesce(func.sum(Subject.weekly_periods), 0))
        .filter(Subject.academic_year_id == academic_year_id)
        .scalar()
        or 0
    )
    if total_periods > 30:
        return [f"Academic year total weekly requirement ({total_periods}) exceeds available slots (30)."]
    return []


def check_faculty_feasibility(db, faculty_id):
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    total_periods = (
        db.query(func.coalesce(func.sum(Subject.weekly_periods), 0))
        .filter(Subject.faculty_id == faculty_id)
        .scalar()
        or 0
    )
    if total_periods > 15:
        name = faculty.name if faculty else "Unknown faculty"
        return [f"Faculty ({name}) is assigned {total_periods} total weekly periods, exceeding the maximum of 15."]
    return []


def check_lab_feasibility(db, academic_year_id):
    lab_rows = db.query(Lab).count()
    # Rough estimate: each lab room has 2 valid block starts per day (P1 and P4), across 5 days.
    # This is an approximation only; it is not a scheduling guarantee.
    available_lab_block_capacity = max(lab_rows * 10, 0)

    total_lab_periods = (
        db.query(func.coalesce(func.sum(Subject.weekly_periods), 0))
        .filter(Subject.academic_year_id == academic_year_id)
        .filter(Subject.subject_type == SubjectType.LAB.value)
        .scalar()
        or 0
    )
    required_lab_blocks = math.ceil(total_lab_periods / 3) if total_lab_periods > 0 else 0

    if required_lab_blocks > available_lab_block_capacity:
        return [
            f"Estimated lab-block requirement ({required_lab_blocks}) exceeds available lab capacity ({available_lab_block_capacity})."
        ]
    return []


def run_full_feasibility_check(db, academic_year_id):
    year_warnings = check_year_feasibility(db, academic_year_id)

    faculty_ids = [
        row[0]
        for row in db.query(Subject.faculty_id)
        .filter(Subject.academic_year_id == academic_year_id)
        .distinct()
        .all()
    ]

    faculty_warnings = {}
    for faculty_id in faculty_ids:
        warnings = check_faculty_feasibility(db, faculty_id)
        if warnings:
            faculty_warnings[faculty_id] = warnings

    lab_warnings = check_lab_feasibility(db, academic_year_id)
    return {
        "year_warnings": year_warnings,
        "faculty_warnings": faculty_warnings,
        "lab_warnings": lab_warnings,
    }
