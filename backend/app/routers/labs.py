from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.core.security import get_user_department_id, require_role
from app.database.database import get_db
from app.models import Faculty, Lab, User
from app.schemas.lab import LabCreate, LabResponse, LabUpdate

router = APIRouter(prefix="/labs", tags=["labs"])


def _duplicate_error_from_integrity(exc_obj: exc.IntegrityError) -> HTTPException:
    message = str(exc_obj.orig).lower()
    if "labs.lab_code" in message or "lab_code" in message:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A lab with this lab code already exists.")
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate lab found.")


@router.post("", response_model=LabResponse)
def create_lab(
    payload: LabCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    lab = Lab(
        department_id=department_id,
        lab_code=payload.lab_code.strip(),
        name=payload.name.strip(),
    )
    try:
        db.add(lab)
        db.commit()
        db.refresh(lab)
        return lab
    except exc.IntegrityError as exc_obj:
        db.rollback()
        raise _duplicate_error_from_integrity(exc_obj)


@router.get("", response_model=list[LabResponse])
def list_labs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    department_id = get_user_department_id(db, current_user)
    return db.query(Lab).filter(Lab.department_id == department_id).order_by(Lab.id.asc()).all()


@router.get("/{lab_id}", response_model=LabResponse)
def get_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    department_id = get_user_department_id(db, current_user)
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if lab is None or lab.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found")
    return lab


@router.put("/{lab_id}", response_model=LabResponse)
def update_lab(
    lab_id: int,
    payload: LabUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if lab is None or lab.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return lab

    for field in ("lab_code", "name"):
        if field in updates and updates[field] is not None:
            setattr(lab, field, updates[field].strip())

    try:
        db.commit()
        db.refresh(lab)
        return lab
    except exc.IntegrityError as exc_obj:
        db.rollback()
        raise _duplicate_error_from_integrity(exc_obj)


@router.delete("/{lab_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if lab is None or lab.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found")

    try:
        db.delete(lab)
        db.commit()
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete lab: it is referenced by existing timetable entries.",
        )
