from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.models import AcademicYear, Lab, Subject, TimetableEntry
from app.models.enums import Period, SubjectType, WeekDay
from app.services.feasibility_checker import run_full_feasibility_check
from app.services.timetable_validator import (
    get_lab_block_periods,
    validate_lab_block,
    validate_single_entry,
)

MAX_NODES = 50000
logger = logging.getLogger(__name__)


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

    subjects = (
        db.query(Subject)
        .filter(Subject.academic_year_id == academic_year_id)
        .order_by(Subject.id)
        .all()
    )

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


def _pending_payload(pending_entries):
    return [
        {
            "academic_year_id": entry.academic_year_id,
            "subject_id": entry.subject_id,
            "faculty_id": entry.faculty_id,
            "day": entry.day,
            "period": entry.period,
            "lab_id": entry.lab_id,
        }
        for entry in pending_entries
    ]


def _count_validator_call(node_counter):
    if node_counter is not None:
        node_counter[0] += 1


def _place_theory_candidate(db, block, pending_entries, day, period, node_counter=None):
    _count_validator_call(node_counter)
    ok, _ = validate_single_entry(
        db,
        academic_year_id=block.academic_year_id,
        subject_id=block.subject_id,
        faculty_id=block.faculty_id,
        day=day,
        period=period,
        lab_id=None,
        subject_type="THEORY",
        pending_entries=_pending_payload(pending_entries),
    )
    if not ok:
        return None
    return PlacedEntry(
        academic_year_id=block.academic_year_id,
        subject_id=block.subject_id,
        faculty_id=block.faculty_id,
        day=day,
        period=period,
        lab_id=None,
    )


def try_place_theory_block(db, block: ScheduleBlock, pending_entries: list[PlacedEntry], node_counter=None):
    for day, period in generate_candidates_for_theory_block(block):
        placed = _place_theory_candidate(db, block, pending_entries, day, period, node_counter)
        if placed is not None:
            return placed
    return None


def _place_lab_candidate(
    db,
    block,
    pending_entries,
    all_lab_ids,
    day,
    start_period,
    lab_id,
    department_id=None,
    node_counter=None,
):
    _count_validator_call(node_counter)
    ok, _ = validate_lab_block(
        db,
        academic_year_id=block.academic_year_id,
        subject_id=block.subject_id,
        faculty_id=block.faculty_id,
        lab_id=lab_id,
        day=day,
        start_period=start_period,
        lab_total_count=len(all_lab_ids),
        department_id=department_id,
        pending_entries=_pending_payload(pending_entries),
    )
    if not ok:
        return None
    return [
        PlacedEntry(
            academic_year_id=block.academic_year_id,
            subject_id=block.subject_id,
            faculty_id=block.faculty_id,
            day=day,
            period=period,
            lab_id=lab_id,
        )
        for period in get_lab_block_periods(start_period)
    ]


def try_place_lab_block(
    db,
    block: ScheduleBlock,
    pending_entries: list[PlacedEntry],
    all_lab_ids: list[int],
    department_id: int | None = None,
    node_counter=None,
):
    for day, start_period, lab_id in generate_candidates_for_lab_block(block, all_lab_ids):
        placed = _place_lab_candidate(
            db,
            block,
            pending_entries,
            all_lab_ids,
            day,
            start_period,
            lab_id,
            department_id=department_id,
            node_counter=node_counter,
        )
        if placed is not None:
            return placed
    return None


def _order_blocks_by_faculty_periods(db, academic_year_id, blocks):
    if not blocks:
        return []
    period_rows = (
        db.query(Subject.faculty_id, Subject.weekly_periods)
        .filter(Subject.academic_year_id == academic_year_id)
        .order_by(Subject.id)
        .all()
    )
    faculty_periods = {}
    for faculty_id, weekly_periods in period_rows:
        faculty_periods[faculty_id] = faculty_periods.get(faculty_id, 0) + weekly_periods
    return sorted(
        blocks,
        key=lambda block: (-faculty_periods.get(block.faculty_id, 0), block.subject_id),
    )


def run_generation(db, academic_year_id, use_backtracking=True):
    loaded = load_blocks_for_year(db, academic_year_id)
    lab_blocks = _order_blocks_by_faculty_periods(db, academic_year_id, loaded["lab_blocks"])
    theory_blocks = _order_blocks_by_faculty_periods(db, academic_year_id, loaded["theory_blocks"])
    unscheduled = []

    for warning in loaded["warnings"]:
        unscheduled.append({"subject_name": "Loader warning", "reason": warning})

    academic_year = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    if academic_year is None:
        all_lab_ids = []
        block_department_id = None
    else:
        block_department_id = academic_year.department_id
        all_lab_ids = [
            lab_id
            for (lab_id,) in db.query(Lab.id)
            .filter(Lab.department_id == block_department_id)
            .order_by(Lab.id)
            .all()
        ]
    blocks = lab_blocks + theory_blocks
    node_counter = [0]
    backtracks = 0
    pending_entries = []
    node_limit_reached = False

    lab_reason = "Could not find a valid 3-consecutive-period slot after trying all days, start periods, and labs."
    theory_reason = "Could not find a valid single-period slot after trying all day/period combinations."

    if not use_backtracking:
        block_unscheduled = []
        for block in lab_blocks:
            placed = try_place_lab_block(
                db,
                block,
                pending_entries,
                all_lab_ids,
                department_id=block_department_id,
                node_counter=node_counter,
            )
            if placed is None:
                block_unscheduled.append({"subject_name": block.subject_name, "reason": lab_reason})
            else:
                pending_entries.extend(placed)
        for block in theory_blocks:
            placed = try_place_theory_block(db, block, pending_entries, node_counter=node_counter)
            if placed is None:
                block_unscheduled.append({"subject_name": block.subject_name, "reason": theory_reason})
            else:
                pending_entries.append(placed)
    else:
        best_placed = []
        best_block_count = 0

        def place_next(block_index):
            nonlocal backtracks, best_placed, best_block_count, node_limit_reached
            if block_index > best_block_count:
                best_block_count = block_index
                best_placed = list(pending_entries)
            if block_index == len(blocks):
                return True
            if node_counter[0] >= MAX_NODES:
                node_limit_reached = True
                return False

            block = blocks[block_index]
            is_lab = block.subject_type == SubjectType.LAB.value
            candidates = (
                generate_candidates_for_lab_block(block, all_lab_ids)
                if is_lab
                else generate_candidates_for_theory_block(block)
            )
            for candidate in candidates:
                if node_counter[0] >= MAX_NODES:
                    node_limit_reached = True
                    return False
                if is_lab:
                    placed = _place_lab_candidate(
                        db,
                        block,
                        pending_entries,
                        all_lab_ids,
                        *candidate,
                        department_id=block_department_id,
                        node_counter=node_counter,
                    )
                else:
                    placed_entry = _place_theory_candidate(
                        db,
                        block,
                        pending_entries,
                        *candidate,
                        node_counter=node_counter,
                    )
                    placed = [placed_entry] if placed_entry is not None else None
                if placed is None:
                    continue

                pending_length = len(pending_entries)
                pending_entries.extend(placed)
                if place_next(block_index + 1):
                    return True
                del pending_entries[pending_length:]
                backtracks += 1
                if node_limit_reached:
                    return False
            return False

        solved = place_next(0)
        pending_entries = best_placed
        if not solved:
            block_unscheduled = []
            reason_suffix = " (after backtracking search)" if node_limit_reached else ""
            for block in blocks[best_block_count:]:
                reason = lab_reason if block.subject_type == SubjectType.LAB.value else theory_reason
                block_unscheduled.append(
                    {"subject_name": block.subject_name, "reason": reason + reason_suffix}
                )
        else:
            block_unscheduled = []

    unscheduled.extend(block_unscheduled)
    logger.info(
        "Timetable generation: blocks=%d nodes=%d backtracks=%d placed=%d unscheduled=%d",
        len(blocks),
        node_counter[0],
        backtracks,
        len(pending_entries),
        len(unscheduled),
    )
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
