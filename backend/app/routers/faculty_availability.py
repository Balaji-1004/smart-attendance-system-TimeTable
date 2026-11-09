from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.core.security import get_user_department_id, require_role
from app.database.database import get_db
from app.models import Faculty, FacultyAvailability, User
from app.schemas.faculty_availability import FacultyAvailabilityCreate, FacultyAvailabilityResponse

router = APIRouter(prefix="/faculty-availability", tags=["faculty-availability"])


def _duplicate_error_from_integrity(exc_obj: exc.IntegrityError) -> HTTPException:
    message = str(exc_obj.orig).lower()
    if "uq_faculty_day_period" in message or "faculty_id" in message and "day" in message and "period" in message:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This faculty is already marked unavailable for that day and period.",
        )
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate faculty availability found.")


@router.post("", response_model=FacultyAvailabilityResponse)
def create_faculty_availability(
    payload: FacultyAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    faculty = db.query(Faculty).filter(Faculty.id == payload.faculty_id).first()
    if faculty is None or faculty.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")

    availability = FacultyAvailability(
        faculty_id=payload.faculty_id,
        day=payload.day,
        period=payload.period,
    )

    try:
        db.add(availability)
        db.commit()
        db.refresh(availability)
        return availability
    except exc.IntegrityError as exc_obj:
        db.rollback()
        raise _duplicate_error_from_integrity(exc_obj)


@router.get("", response_model=list[FacultyAvailabilityResponse])
def list_faculty_availability(
    faculty_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    query = db.query(FacultyAvailability).join(Faculty, Faculty.id == FacultyAvailability.faculty_id).filter(Faculty.department_id == department_id)
    if faculty_id is not None:
        query = query.filter(FacultyAvailability.faculty_id == faculty_id)
    return query.order_by(FacultyAvailability.id.asc()).all()


@router.delete("/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty_availability(
    availability_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    availability = db.query(FacultyAvailability).filter(FacultyAvailability.id == availability_id).first()
    if availability is None or availability.faculty.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty availability record not found")

    db.delete(availability)
    db.commit()
