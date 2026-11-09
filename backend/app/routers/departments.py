from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_user_department_id, require_role
from app.database.database import get_db
from app.models import Department, User
from app.schemas.department import DepartmentResponse

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("/me", response_model=DepartmentResponse)
def get_current_department(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY", "STUDENT")),
):
    department_id = get_user_department_id(db, current_user)
    department = db.query(Department).filter(Department.id == department_id).first()
    if department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return department
