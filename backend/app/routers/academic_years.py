from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.core.security import get_user_department_id, require_role
from app.database.database import get_db
from app.models import AcademicYear, Programme, User
from app.schemas.academic_year import AcademicYearCreate, AcademicYearResponse

router = APIRouter(prefix="/academic-years", tags=["academic-years"])


@router.post("", response_model=AcademicYearResponse)
def create_academic_year(
    payload: AcademicYearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    programme = (
        db.query(Programme)
        .filter(Programme.id == payload.programme_id, Programme.department_id == department_id)
        .first()
    )
    if programme is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found")

    obj = AcademicYear(
        department_id=department_id,
        programme_id=programme.id,
        name=payload.name.strip(),
    )
    try:
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Academic year '{payload.name.strip()}' already exists for this programme.",
        )


@router.get("", response_model=list[AcademicYearResponse])
def list_academic_years(
    programme_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    department_id = get_user_department_id(db, current_user)
    query = db.query(AcademicYear).filter(AcademicYear.department_id == department_id)
    if programme_id is not None:
        programme = (
            db.query(Programme)
            .filter(Programme.id == programme_id, Programme.department_id == department_id)
            .first()
        )
        if programme is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found")
        query = query.filter(AcademicYear.programme_id == programme_id)
    return query.order_by(AcademicYear.created_at.desc()).all()


@router.get("/{academic_year_id}", response_model=AcademicYearResponse)
def get_academic_year(
    academic_year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    department_id = get_user_department_id(db, current_user)
    obj = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    if obj is None or obj.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
    return obj


@router.put("/{academic_year_id}", response_model=AcademicYearResponse)
def update_academic_year(
    academic_year_id: int,
    payload: AcademicYearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    obj = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    if obj is None or obj.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
    programme = (
        db.query(Programme)
        .filter(Programme.id == payload.programme_id, Programme.department_id == department_id)
        .first()
    )
    if programme is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found")
    obj.department_id = department_id
    obj.programme_id = programme.id
    obj.name = payload.name.strip()
    try:
        db.commit()
        db.refresh(obj)
        return obj
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Academic year '{payload.name.strip()}' already exists for this programme.",
        )


@router.delete("/{academic_year_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_academic_year(
    academic_year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    obj = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    if obj is None or obj.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")

    try:
        db.delete(obj)
        db.commit()
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Academic year has dependent records and cannot be deleted.",
        )
