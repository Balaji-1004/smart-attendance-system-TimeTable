from __future__ import annotations

from typing import Optional

from app.models import FacultyAvailability, TimetableEntry
from app.models.enums import Period

# Lunch cannot be scheduled and no Saturday/Sunday entries are not implemented as runtime checks here
# because the model schema already structurally forbids them: Period only includes P1-P6 and WeekDay only
# includes MONDAY-FRIDAY, so there is no lunch slot or weekend slot to validate against.


def _normalize_value(value):
    if hasattr(value, "value"):
        return value.value
    return value


def _normalize_pending_entries(pending_entries=None):
    if pending_entries is None:
        return []
    return list(pending_entries)


def _pending_get(pending, key):
    if hasattr(pending, key):
        return getattr(pending, key)
    if isinstance(pending, dict):
        return pending.get(key)
    return None


def get_lab_block_periods(start_period: Period):
    start = _normalize_value(start_period)
    if start == Period.P1.value:
        return [Period.P1, Period.P2, Period.P3]
    if start == Period.P4.value:
        return [Period.P4, Period.P5, Period.P6]
    return None


def check_year_clash(db, academic_year_id, day, period, pending_entries=None, exclude_entry_id=None):
    day = _normalize_value(day)
    period = _normalize_value(period)

    for entry in db.query(TimetableEntry).filter(
        TimetableEntry.academic_year_id == academic_year_id,
        TimetableEntry.day == day,
        TimetableEntry.period == period,
    ).all():
        if exclude_entry_id is None or entry.id != exclude_entry_id:
            return False, "Academic year slot already occupied."

    for pending in _normalize_pending_entries(pending_entries):
        if (
            _normalize_value(_pending_get(pending, "academic_year_id")) == academic_year_id
            and _normalize_value(_pending_get(pending, "day")) == day
            and _normalize_value(_pending_get(pending, "period")) == period
            and (exclude_entry_id is None or _pending_get(pending, "id") != exclude_entry_id)
        ):
            return False, "Academic year slot already occupied."

    return True, None


def check_faculty_clash(db, faculty_id, day, period, pending_entries=None, exclude_entry_id=None):
    day = _normalize_value(day)
    period = _normalize_value(period)

    for entry in db.query(TimetableEntry).filter(
        TimetableEntry.faculty_id == faculty_id,
        TimetableEntry.day == day,
        TimetableEntry.period == period,
    ).all():
        if exclude_entry_id is None or entry.id != exclude_entry_id:
            return False, "Faculty is already assigned in this slot."

    for pending in _normalize_pending_entries(pending_entries):
        if (
            _pending_get(pending, "faculty_id") == faculty_id
            and _normalize_value(_pending_get(pending, "day")) == day
            and _normalize_value(_pending_get(pending, "period")) == period
            and (exclude_entry_id is None or _pending_get(pending, "id") != exclude_entry_id)
        ):
            return False, "Faculty is already assigned in this slot."

    return True, None


def check_lab_clash(db, lab_id, day, period, pending_entries=None, exclude_entry_id=None):
    if lab_id is None:
        return True, None
    day = _normalize_value(day)
    period = _normalize_value(period)

    for entry in db.query(TimetableEntry).filter(
        TimetableEntry.lab_id == lab_id,
        TimetableEntry.day == day,
        TimetableEntry.period == period,
    ).all():
        if exclude_entry_id is None or entry.id != exclude_entry_id:
            return False, "Laboratory room is already booked in this slot."

    for pending in _normalize_pending_entries(pending_entries):
        if (
            _pending_get(pending, "lab_id") == lab_id
            and _normalize_value(_pending_get(pending, "day")) == day
            and _normalize_value(_pending_get(pending, "period")) == period
            and (exclude_entry_id is None or _pending_get(pending, "id") != exclude_entry_id)
        ):
            return False, "Laboratory room is already booked in this slot."

    return True, None


def check_faculty_daily_limit(db, faculty_id, day, pending_entries=None, exclude_entry_id=None):
    day = _normalize_value(day)
    existing_count = db.query(TimetableEntry).filter(
        TimetableEntry.faculty_id == faculty_id,
        TimetableEntry.day == day,
    ).count()

    pending_count = 0
    for pending in _normalize_pending_entries(pending_entries):
        if (
            _pending_get(pending, "faculty_id") == faculty_id
            and _normalize_value(_pending_get(pending, "day")) == day
            and (exclude_entry_id is None or _pending_get(pending, "id") != exclude_entry_id)
        ):
            pending_count += 1

    total = existing_count + pending_count
    if total > 3:
        return False, "Faculty exceeds the daily limit of 3 periods."
    return True, None


def check_faculty_weekly_limit(db, faculty_id, pending_entries=None, exclude_entry_id=None):
    existing_count = db.query(TimetableEntry).filter(TimetableEntry.faculty_id == faculty_id).count()

    pending_count = 0
    for pending in _normalize_pending_entries(pending_entries):
        if (
            _pending_get(pending, "faculty_id") == faculty_id
            and (exclude_entry_id is None or _pending_get(pending, "id") != exclude_entry_id)
        ):
            pending_count += 1

    total = existing_count + pending_count
    if total > 15:
        return False, "Faculty exceeds the weekly limit of 15 periods."
    return True, None


def check_faculty_availability(db, faculty_id, day, period):
    day = _normalize_value(day)
    period = _normalize_value(period)
    exists = db.query(FacultyAvailability).filter(
        FacultyAvailability.faculty_id == faculty_id,
        FacultyAvailability.day == day,
        FacultyAvailability.period == period,
    ).first()
    if exists:
        return False, "Faculty is marked unavailable for this slot."
    return True, None


def check_lab_room_consistency(subject_type, lab_id):
    subject_type = _normalize_value(subject_type)
    if subject_type == "LAB" and lab_id is None:
        return False, "Lab subjects must be assigned a laboratory room."
    if subject_type == "THEORY" and lab_id is not None:
        return False, "Theory subjects must not be assigned a laboratory room."
    return True, None


def check_lab_concurrency(db, day, period, lab_total_count, pending_entries=None, exclude_entry_ids=None):
    day = _normalize_value(day)
    period = _normalize_value(period)
    excluded = set() if exclude_entry_ids is None else set(exclude_entry_ids)

    existing_count = db.query(TimetableEntry).filter(
        TimetableEntry.day == day,
        TimetableEntry.period == period,
        TimetableEntry.lab_id.isnot(None),
    ).count()

    pending_count = 0
    for pending in _normalize_pending_entries(pending_entries):
        pid = _pending_get(pending, "id")
        if pid in excluded:
            continue
        if (
            _normalize_value(_pending_get(pending, "day")) == day
            and _normalize_value(_pending_get(pending, "period")) == period
            and _pending_get(pending, "lab_id") is not None
        ):
            pending_count += 1

    total = existing_count + pending_count
    if total >= lab_total_count:
        return False, "All lab rooms are occupied in this slot."
    return True, None


def validate_single_entry(db, academic_year_id, subject_id, faculty_id, day, period, lab_id, subject_type, pending_entries=None, exclude_entry_id=None):
    checks = [
        check_year_clash,
        check_faculty_clash,
        check_lab_clash,
        check_faculty_daily_limit,
        check_faculty_weekly_limit,
        check_faculty_availability,
        check_lab_room_consistency,
    ]
    reasons = []

    for check in checks:
        if check is check_year_clash:
            ok, reason = check(db, academic_year_id, day, period, pending_entries=pending_entries, exclude_entry_id=exclude_entry_id)
        elif check is check_faculty_clash:
            ok, reason = check(db, faculty_id, day, period, pending_entries=pending_entries, exclude_entry_id=exclude_entry_id)
        elif check is check_lab_clash:
            ok, reason = check(db, lab_id, day, period, pending_entries=pending_entries, exclude_entry_id=exclude_entry_id)
        elif check is check_faculty_daily_limit:
            ok, reason = check(db, faculty_id, day, pending_entries=pending_entries, exclude_entry_id=exclude_entry_id)
        elif check is check_faculty_weekly_limit:
            ok, reason = check(db, faculty_id, pending_entries=pending_entries, exclude_entry_id=exclude_entry_id)
        elif check is check_faculty_availability:
            ok, reason = check(db, faculty_id, day, period)
        elif check is check_lab_room_consistency:
            ok, reason = check(subject_type, lab_id)
        else:
            continue

        if not ok and reason:
            reasons.append(reason)

    if reasons:
        return False, reasons
    return True, []


def validate_lab_block(db, academic_year_id, subject_id, faculty_id, lab_id, day, start_period, lab_total_count, pending_entries=None, exclude_entry_ids=None):
    periods = get_lab_block_periods(start_period)
    if periods is None:
        return False, ["Lab sessions must start at P1 or P4 to occupy 3 consecutive periods without crossing lunch or the day boundary."]

    combined_pending = list(pending_entries or [])
    reasons = []
    seen = set()
    for period in periods:
        year_ok, year_reason = check_year_clash(db, academic_year_id, day, period, pending_entries=combined_pending, exclude_entry_id=None)
        if not year_ok and year_reason and year_reason not in seen:
            seen.add(year_reason)
            reasons.append(f"{period.value}: {year_reason}")

        faculty_ok, faculty_reason = check_faculty_clash(db, faculty_id, day, period, pending_entries=combined_pending, exclude_entry_id=None)
        if not faculty_ok and faculty_reason and faculty_reason not in seen:
            seen.add(faculty_reason)
            reasons.append(f"{period.value}: {faculty_reason}")

        lab_ok, lab_reason = check_lab_clash(db, lab_id, day, period, pending_entries=combined_pending, exclude_entry_id=None)
        if not lab_ok and lab_reason and lab_reason not in seen:
            seen.add(lab_reason)
            reasons.append(f"{period.value}: {lab_reason}")

        avail_ok, avail_reason = check_faculty_availability(db, faculty_id, day, period)
        if not avail_ok and avail_reason and avail_reason not in seen:
            seen.add(avail_reason)
            reasons.append(f"{period.value}: {avail_reason}")

        concurrency_ok, concurrency_reason = check_lab_concurrency(db, day, period, lab_total_count, pending_entries=combined_pending, exclude_entry_ids=exclude_entry_ids)
        if not concurrency_ok and concurrency_reason and concurrency_reason not in seen:
            seen.add(concurrency_reason)
            reasons.append(f"{period.value}: {concurrency_reason}")

    daily_ok, daily_reason = check_faculty_daily_limit(db, faculty_id, day, pending_entries=combined_pending, exclude_entry_id=None)
    if not daily_ok and daily_reason and daily_reason not in seen:
        seen.add(daily_reason)
        reasons.append(daily_reason)

    weekly_ok, weekly_reason = check_faculty_weekly_limit(db, faculty_id, pending_entries=combined_pending, exclude_entry_id=None)
    if not weekly_ok and weekly_reason and weekly_reason not in seen:
        seen.add(weekly_reason)
        reasons.append(weekly_reason)

    if reasons:
        return False, reasons
    return True, []
