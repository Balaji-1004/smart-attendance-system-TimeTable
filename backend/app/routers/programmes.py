from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.core.security import get_user_department_id, require_role
from app.database.database import get_db
from app.models import AcademicYear, Programme, User
from app.schemas.programme import ProgrammeCreate, ProgrammeResponse, ProgrammeUpdate

router = APIRouter(prefix="/programmes", tags=["programmes"])


@router.get("", response_model=list[ProgrammeResponse])
def list_programmes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    department_id = get_user_department_id(db, current_user)
    return (
        db.query(Programme)
        .filter(Programme.department_id == department_id)
        .order_by(Programme.id)
        .all()
    )


@router.post("", response_model=ProgrammeResponse)
def create_programme(
    payload: ProgrammeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    programme = Programme(
        department_id=get_user_department_id(db, current_user),
        name=payload.name.strip(),
    )
    try:
        db.add(programme)
        db.commit()
        db.refresh(programme)
        return programme
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Programme '{payload.name.strip()}' already exists for this department.",
        )


@router.put("/{programme_id}", response_model=ProgrammeResponse)
def update_programme(
    programme_id: int,
    payload: ProgrammeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    programme = (
        db.query(Programme)
        .filter(Programme.id == programme_id, Programme.department_id == department_id)
        .first()
    )
    if programme is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found")
    programme.name = payload.name.strip()
    try:
        db.commit()
        db.refresh(programme)
        return programme
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Programme '{payload.name.strip()}' already exists for this department.",
        )


@router.delete("/{programme_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_programme(
    programme_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    programme = (
        db.query(Programme)
        .filter(Programme.id == programme_id, Programme.department_id == department_id)
        .first()
    )
    if programme is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found")
    if db.query(AcademicYear.id).filter(AcademicYear.programme_id == programme.id).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Programme has academic years and cannot be deleted.",
        )
    db.delete(programme)
    db.commit()
