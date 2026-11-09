from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.models import FacultyAvailability, TimetableEntry
from app.models.enums import Period
from app.services.timetable_validator import (
    check_faculty_clash,
    check_lab_room_consistency,
    check_year_clash,
    validate_lab_block,
    validate_single_entry,
)


def make_db(existing_rows=None, unavailable_slots=None):
    existing_rows = existing_rows or []
    unavailable_slots = unavailable_slots or []

    def build_query(rows):
        query = MagicMock()
        query.filter.return_value.all.return_value = rows
        query.filter.return_value.count.return_value = len(rows)
        query.filter.return_value.first.return_value = rows[0] if rows else None
        return query

    db = MagicMock()

    def query_side_effect(model):
        if model is TimetableEntry:
            return build_query(existing_rows)
        if model is FacultyAvailability:
            return build_query(unavailable_slots)
        return build_query([])

    db.query.side_effect = query_side_effect
    return db


def test_pytest_package_imports_cleanly():
    assert pytest.__version__


def test_check_year_clash_detects_conflict():
    row = SimpleNamespace(academic_year_id=1, day="Monday", period=Period.P2.value, id=7)
    db = make_db(existing_rows=[row])

    ok, reason = check_year_clash(db, academic_year_id=1, day="Monday", period=Period.P2)

    assert ok is False
    assert "Academic year slot already occupied" in reason


def test_validate_single_entry_rejects_lab_subject_without_lab():
    db = make_db()

    ok, reasons = validate_single_entry(
        db,
        academic_year_id=1,
        subject_id=2,
        faculty_id=5,
        day="Monday",
        period=Period.P1,
        lab_id=None,
        subject_type="LAB",
    )

    assert ok is False
    assert any("Lab subjects must be assigned a laboratory room" in reason for reason in reasons)


def test_validate_lab_block_requires_valid_three_period_window():
    db = make_db()

    ok, reasons = validate_lab_block(
        db,
        academic_year_id=1,
        subject_id=2,
        faculty_id=5,
        lab_id=1,
        day="Monday",
        start_period=Period.P2,
        lab_total_count=2,
    )

    assert ok is False
    assert any("Lab sessions must start at P1 or P4" in reason for reason in reasons)


def test_check_faculty_clash_detects_overlap():
    db = make_db(existing_rows=[SimpleNamespace(faculty_id=2, day="Monday", period=Period.P3.value, id=3)])

    ok, reason = check_faculty_clash(db, faculty_id=2, day="Monday", period=Period.P3)

    assert ok is False
    assert "Faculty is already assigned in this slot" in reason


def test_check_lab_room_consistency_accepts_theory_without_lab():
    ok, reason = check_lab_room_consistency("THEORY", None)

    assert ok is True
    assert reason is None

