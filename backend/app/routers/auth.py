from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_user_department_id, verify_password
from app.database.database import get_db
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    department_id = get_user_department_id(db, user)
    token_payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "department_id": department_id,
        "faculty_id": user.faculty_id,
        "student_id": user.student_id,
    }
    token = create_access_token(token_payload)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role.value,
        username=user.username,
        department_id=department_id,
        faculty_id=user.faculty_id,
        student_id=user.student_id,
    )
