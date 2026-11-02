from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.database import get_db
from app.models import AcademicYear, Faculty, Lab, Subject, TimetableEntry, User
from app.schemas.timetable import (
    DepartmentTimetableEntryResponse,
    TimetableEntryResponse,
    TimetableEntryUpdate,
    TimetableGenerateRequest,
    TimetableGenerateResponse,
)
from app.services.timetable_generator import generate_timetable
from app.services.timetable_validator import validate_single_entry

router = APIRouter(prefix="/timetable", tags=["timetable"])


def _entry_to_response(entry: TimetableEntry) -> TimetableEntryResponse:
    subject = entry.subject
    faculty = entry.faculty
    lab = entry.lab
    return TimetableEntryResponse(
        id=entry.id,
        academic_year_id=entry.academic_year_id,
        subject_id=entry.subject_id,
        subject_name=subject.name,
        faculty_id=entry.faculty_id,
        faculty_name=faculty.name,
        day=entry.day,
        period=entry.period,
        lab_id=entry.lab_id,
        lab_name=lab.name if lab else None,
    )


def _entry_to_department_response(entry: TimetableEntry) -> DepartmentTimetableEntryResponse:
    response = _entry_to_response(entry)
    return DepartmentTimetableEntryResponse(
        id=response.id,
        academic_year_id=response.academic_year_id,
        subject_id=response.subject_id,
        subject_name=response.subject_name,
        faculty_id=response.faculty_id,
        faculty_name=response.faculty_name,
        day=response.day,
        period=response.period,
        lab_id=response.lab_id,
        lab_name=response.lab_name,
        academic_year_name=entry.academic_year.name,
    )


def _serialize_pending_entries(db: Session, academic_year_id: int, exclude_entry_id: int | None = None):
    query = db.query(TimetableEntry).filter(TimetableEntry.academic_year_id == academic_year_id)
    if exclude_entry_id is not None:
        query = query.filter(TimetableEntry.id != exclude_entry_id)
    entries = query.all()
    payload = []
    for entry in entries:
        payload.append(
            {
                "id": entry.id,
                "academic_year_id": entry.academic_year_id,
                "subject_id": entry.subject_id,
                "faculty_id": entry.faculty_id,
                "day": entry.day,
                "period": entry.period,
                "lab_id": entry.lab_id,
            }
        )
    return payload


@router.post("/generate", response_model=TimetableGenerateResponse)
def generate_timetable_route(
    payload: TimetableGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    academic_year = db.query(AcademicYear).filter(AcademicYear.id == payload.academic_year_id).first()
    if academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")

    result = generate_timetable(db, payload.academic_year_id)
    return result


@router.get("/year/{year_id}", response_model=list[TimetableEntryResponse])
def get_timetable_for_year(
    year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    academic_year = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
    if academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")

    entries = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.academic_year_id == year_id)
        .join(Subject, Subject.id == TimetableEntry.subject_id)
        .join(Faculty, Faculty.id == TimetableEntry.faculty_id)
        .outerjoin(Lab, Lab.id == TimetableEntry.lab_id)
        .order_by(TimetableEntry.day, TimetableEntry.period)
        .all()
    )
    return [_entry_to_response(entry) for entry in entries]


@router.get("/faculty/{faculty_id}", response_model=list[TimetableEntryResponse])
def get_timetable_for_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if faculty is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")

    if current_user.role.value == "FACULTY" and current_user.faculty_id != faculty_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own faculty timetable.")

    entries = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.faculty_id == faculty_id)
        .join(Subject, Subject.id == TimetableEntry.subject_id)
        .join(Faculty, Faculty.id == TimetableEntry.faculty_id)
        .outerjoin(Lab, Lab.id == TimetableEntry.lab_id)
        .order_by(TimetableEntry.day, TimetableEntry.period)
        .all()
    )
    return [_entry_to_response(entry) for entry in entries]


@router.get("/department", response_model=list[DepartmentTimetableEntryResponse])
def get_department_timetable(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    entries = (
        db.query(TimetableEntry)
        .join(Subject, Subject.id == TimetableEntry.subject_id)
        .join(Faculty, Faculty.id == TimetableEntry.faculty_id)
        .join(AcademicYear, AcademicYear.id == TimetableEntry.academic_year_id)
        .outerjoin(Lab, Lab.id == TimetableEntry.lab_id)
        .order_by(AcademicYear.id, TimetableEntry.day, TimetableEntry.period)
        .all()
    )
    return [_entry_to_department_response(entry) for entry in entries]


@router.put("/{entry_id}", response_model=TimetableEntryResponse)
def update_timetable_entry(
    entry_id: int,
    payload: TimetableEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    entry = db.query(TimetableEntry).filter(TimetableEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable entry not found")

    if current_user.role.value == "FACULTY" and entry.faculty_id != current_user.faculty_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit your own timetable entries.")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _entry_to_response(entry)

    new_day = updates.get("day", entry.day)
    new_period = updates.get("period", entry.period)
    new_lab_id = updates.get("lab_id", entry.lab_id)

    if new_day == entry.day and new_period == entry.period and new_lab_id == entry.lab_id:
        return _entry_to_response(entry)

    validation_payload = _serialize_pending_entries(db, entry.academic_year_id, exclude_entry_id=entry_id)
    valid, reasons = validate_single_entry(
        db,
        academic_year_id=entry.academic_year_id,
        subject_id=entry.subject_id,
        faculty_id=entry.faculty_id,
        day=new_day,
        period=new_period,
        lab_id=new_lab_id,
        subject_type=entry.subject.subject_type,
        pending_entries=validation_payload,
        exclude_entry_id=entry_id,
    )
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reasons)

    entry.day = new_day
    entry.period = new_period
    entry.lab_id = new_lab_id
    db.commit()
    db.refresh(entry)
    return _entry_to_response(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timetable_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    entry = db.query(TimetableEntry).filter(TimetableEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable entry not found")

    if current_user.role.value == "FACULTY" and entry.faculty_id != current_user.faculty_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own timetable entries.")

    db.delete(entry)
    db.commit()
