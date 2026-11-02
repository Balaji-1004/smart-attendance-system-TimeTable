from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.database import get_db
from app.models import AcademicYear, Faculty, Subject, User
from app.models.enums import SubjectType
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate

router = APIRouter(prefix="/subjects", tags=["subjects"])


def _duplicate_error_from_integrity(exc_obj: exc.IntegrityError) -> HTTPException:
    message = str(exc_obj.orig).lower()
    if "uq_year_code" in message or "academic_year_id" in message and "code" in message:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subject code already exists for this academic year.",
        )
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate subject found.")


@router.post("", response_model=SubjectResponse)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    academic_year = db.query(AcademicYear).filter(AcademicYear.id == payload.academic_year_id).first()
    if academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")

    faculty = db.query(Faculty).filter(Faculty.id == payload.faculty_id).first()
    if faculty is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")

    subject = Subject(
        academic_year_id=payload.academic_year_id,
        name=payload.name.strip(),
        code=payload.code.strip(),
        subject_type=payload.subject_type.value,
        weekly_periods=payload.weekly_periods,
        faculty_id=payload.faculty_id,
    )

    try:
        db.add(subject)
        db.commit()
        db.refresh(subject)
        return subject
    except exc.IntegrityError as exc_obj:
        db.rollback()
        raise _duplicate_error_from_integrity(exc_obj)


@router.get("", response_model=list[SubjectResponse])
def list_subjects(
    academic_year_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    query = db.query(Subject)
    if academic_year_id is not None:
        query = query.filter(Subject.academic_year_id == academic_year_id)
    return query.order_by(Subject.created_at.desc()).all()


@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject


@router.put("/{subject_id}", response_model=SubjectResponse)
def update_subject(
    subject_id: int,
    payload: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return subject

    if "faculty_id" in updates and updates["faculty_id"] is not None:
        faculty = db.query(Faculty).filter(Faculty.id == updates["faculty_id"]).first()
        if faculty is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")
        subject.faculty_id = updates["faculty_id"]

    for field in ("name", "code"):
        if field in updates and updates[field] is not None:
            setattr(subject, field, updates[field].strip())

    if "subject_type" in updates and updates["subject_type"] is not None:
        subject.subject_type = updates["subject_type"].value

    if "weekly_periods" in updates and updates["weekly_periods"] is not None:
        subject.weekly_periods = updates["weekly_periods"]

    try:
        db.commit()
        db.refresh(subject)
        return subject
    except exc.IntegrityError as exc_obj:
        db.rollback()
        raise _duplicate_error_from_integrity(exc_obj)


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    try:
        db.delete(subject)
        db.commit()
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete subject: it is referenced by existing timetable entries or attendance records.",
        )
