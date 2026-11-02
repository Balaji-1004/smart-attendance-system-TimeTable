from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models import Lab, Subject, TimetableEntry
from app.models.enums import Period, SubjectType, WeekDay
from app.services.feasibility_checker import run_full_feasibility_check
from app.services.timetable_validator import (
    get_lab_block_periods,
    validate_lab_block,
    validate_single_entry,
)


@dataclass
class ScheduleBlock:
    subject_id: int
    subject_name: str
    faculty_id: int
    academic_year_id: int
    subject_type: str
    duration: int
    lab_id: Optional[int] = None


@dataclass
class PlacedEntry:
    academic_year_id: int
    subject_id: int
    faculty_id: int
    day: WeekDay
    period: Period
    lab_id: Optional[int] = None


def load_blocks_for_year(db, academic_year_id):
    lab_blocks = []
    theory_blocks = []
    warnings = []

    subjects = db.query(Subject).filter(Subject.academic_year_id == academic_year_id).all()

    for subject in subjects:
        subject_name = subject.name
        raw_type = subject.subject_type
        subject_type = raw_type.value if hasattr(raw_type, "value") else str(raw_type).upper()

        if subject_type == SubjectType.THEORY.value:
            for _ in range(subject.weekly_periods):
                theory_blocks.append(
                    ScheduleBlock(
                        subject_id=subject.id,
                        subject_name=subject_name,
                        faculty_id=subject.faculty_id,
                        academic_year_id=subject.academic_year_id,
                        subject_type=SubjectType.THEORY.value,
                        duration=1,
                        lab_id=None,
                    )
                )
            continue

        if subject_type == SubjectType.LAB.value:
            full_blocks = subject.weekly_periods // 3
            remainder = subject.weekly_periods % 3

            if remainder != 0:
                warnings.append(
                    f"Subject '{subject_name}' has weekly_periods={subject.weekly_periods} which is not a multiple of 3; only whole 3-period lab blocks will be scheduled, {remainder} periods will be unmet."
                )

            for _ in range(full_blocks):
                lab_blocks.append(
                    ScheduleBlock(
                        subject_id=subject.id,
                        subject_name=subject_name,
                        faculty_id=subject.faculty_id,
                        academic_year_id=subject.academic_year_id,
                        subject_type=SubjectType.LAB.value,
                        duration=3,
                        lab_id=None,
                    )
                )

    return {
        "lab_blocks": lab_blocks,
        "theory_blocks": theory_blocks,
        "warnings": warnings,
    }


def generate_candidates_for_theory_block(block: ScheduleBlock):
    slots = []
    for day in WeekDay:
        for period in Period:
            slots.append((day, period))
    return slots


def generate_candidates_for_lab_block(block: ScheduleBlock, all_lab_ids: list[int]):
    candidates = []
    for day in WeekDay:
        for start_period in [Period.P1, Period.P4]:
            for lab_id in all_lab_ids:
                candidates.append((day, start_period, lab_id))
    return candidates


def try_place_theory_block(db, block: ScheduleBlock, pending_entries: list[PlacedEntry]):
    for day, period in generate_candidates_for_theory_block(block):
        ok, _ = validate_single_entry(
            db,
            academic_year_id=block.academic_year_id,
            subject_id=block.subject_id,
            faculty_id=block.faculty_id,
            day=day,
            period=period,
            lab_id=None,
            subject_type="THEORY",
            pending_entries=[
                {
                    "academic_year_id": entry.academic_year_id,
                    "subject_id": entry.subject_id,
                    "faculty_id": entry.faculty_id,
                    "day": entry.day,
                    "period": entry.period,
                    "lab_id": entry.lab_id,
                }
                for entry in pending_entries
            ],
        )
        if ok:
            return PlacedEntry(
                academic_year_id=block.academic_year_id,
                subject_id=block.subject_id,
                faculty_id=block.faculty_id,
                day=day,
                period=period,
                lab_id=None,
            )
    return None


def try_place_lab_block(db, block: ScheduleBlock, pending_entries: list[PlacedEntry], all_lab_ids: list[int]):
    for day, start_period, lab_id in generate_candidates_for_lab_block(block, all_lab_ids):
        ok, _ = validate_lab_block(
            db,
            academic_year_id=block.academic_year_id,
            subject_id=block.subject_id,
            faculty_id=block.faculty_id,
            lab_id=lab_id,
            day=day,
            start_period=start_period,
            lab_total_count=len(all_lab_ids),
            pending_entries=[
                {
                    "academic_year_id": entry.academic_year_id,
                    "subject_id": entry.subject_id,
                    "faculty_id": entry.faculty_id,
                    "day": entry.day,
                    "period": entry.period,
                    "lab_id": entry.lab_id,
                }
                for entry in pending_entries
            ],
        )
        if ok:
            placed = []
            for period in get_lab_block_periods(start_period):
                placed.append(
                    PlacedEntry(
                        academic_year_id=block.academic_year_id,
                        subject_id=block.subject_id,
                        faculty_id=block.faculty_id,
                        day=day,
                        period=period,
                        lab_id=lab_id,
                    )
                )
            return placed
    return None


def run_generation(db, academic_year_id):
    loaded = load_blocks_for_year(db, academic_year_id)
    lab_blocks = loaded["lab_blocks"]
    theory_blocks = loaded["theory_blocks"]
    unscheduled = []

    for warning in loaded["warnings"]:
        unscheduled.append({"subject_name": "Loader warning", "reason": warning})

    all_lab_ids = [lab.id for lab in db.query(Lab).all()]
    pending_entries = []

    for block in lab_blocks:
        placed = try_place_lab_block(db, block, pending_entries, all_lab_ids)
        if placed is None:
            unscheduled.append({
                "subject_name": block.subject_name,
                "reason": "Could not find a valid 3-consecutive-period slot after trying all days, start periods, and labs.",
            })
        else:
            pending_entries.extend(placed)

    for block in theory_blocks:
        placed = try_place_theory_block(db, block, pending_entries)
        if placed is None:
            unscheduled.append({
                "subject_name": block.subject_name,
                "reason": "Could not find a valid single-period slot after trying all day/period combinations.",
            })
        else:
            pending_entries.append(placed)

    return {"placed": pending_entries, "unscheduled": unscheduled}


def generate_timetable(db, academic_year_id):
    """Perform a destructive regeneration for an academic year.

    This function deletes existing TimetableEntry rows for the target year before regenerating.
    Any user-facing warning like 'Regenerating will discard existing timetable changes' belongs in
    the API route/frontend layer; this service function does not ask for confirmation.
    """
    feasibility = run_full_feasibility_check(db, academic_year_id)

    try:
        db.query(TimetableEntry).filter(TimetableEntry.academic_year_id == academic_year_id).delete()
        placed_result = run_generation(db, academic_year_id)
        placed = placed_result["placed"]
        unscheduled = placed_result["unscheduled"]

        for entry in placed:
            db.add(
                TimetableEntry(
                    academic_year_id=entry.academic_year_id,
                    subject_id=entry.subject_id,
                    faculty_id=entry.faculty_id,
                    day=entry.day,
                    period=entry.period,
                    lab_id=entry.lab_id,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "feasibility_warnings": feasibility,
        "placed_count": len(placed),
        "unscheduled": unscheduled,
    }
