from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.database import get_db
from app.models import AcademicYear, Department, User
from app.schemas.academic_year import AcademicYearCreate, AcademicYearResponse

router = APIRouter(prefix="/academic-years", tags=["academic-years"])


@router.post("", response_model=AcademicYearResponse)
def create_academic_year(
    payload: AcademicYearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department = db.query(Department).filter(Department.id == payload.department_id).first()
    if department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    obj = AcademicYear(department_id=payload.department_id, name=payload.name.strip())
    try:
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Academic year '{payload.name.strip()}' already exists for this department.",
        )


@router.get("", response_model=list[AcademicYearResponse])
def list_academic_years(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    return db.query(AcademicYear).order_by(AcademicYear.created_at.desc()).all()


@router.get("/{academic_year_id}", response_model=AcademicYearResponse)
def get_academic_year(
    academic_year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    obj = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
    return obj


@router.put("/{academic_year_id}", response_model=AcademicYearResponse)
def update_academic_year(
    academic_year_id: int,
    payload: AcademicYearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    obj = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")

    department = db.query(Department).filter(Department.id == payload.department_id).first()
    if department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    obj.department_id = payload.department_id
    obj.name = payload.name.strip()
    try:
        db.commit()
        db.refresh(obj)
        return obj
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Academic year '{payload.name.strip()}' already exists for this department.",
        )


@router.delete("/{academic_year_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_academic_year(
    academic_year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    obj = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    if obj is None:
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
