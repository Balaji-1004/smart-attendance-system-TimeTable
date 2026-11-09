from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.core.security import get_user_department_id, hash_password, require_role
from app.database.database import get_db
from app.models import Faculty, User
from app.models.user import Role
from app.schemas.faculty import FacultyCreate, FacultyResponse, FacultyUpdate

router = APIRouter(prefix="/faculty", tags=["faculty"])


def _duplicate_error_from_integrity(exc_obj: exc.IntegrityError) -> HTTPException:
    message = str(exc_obj.orig).lower()
    if "faculty.faculty_code" in message:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A faculty with this faculty code already exists.")
    if "faculty.email" in message:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A faculty with this email already exists.")
    if "users.username" in message:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this username already exists.")
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate record found.")


def _serialize_faculty(db: Session, faculty: Faculty) -> dict:
    user_id = db.query(User.id).filter(User.faculty_id == faculty.id).scalar()
    return {
        "id": faculty.id,
        "department_id": faculty.department_id,
        "name": faculty.name,
        "faculty_code": faculty.faculty_code,
        "email": faculty.email,
        "user_id": user_id,
        "created_at": faculty.created_at,
    }


@router.post("", response_model=FacultyResponse)
def create_faculty(
    payload: FacultyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    faculty = Faculty(
        department_id=department_id,
        name=payload.name.strip(),
        faculty_code=payload.faculty_code.strip(),
        email=payload.email.strip(),
    )

    try:
        db.add(faculty)
        db.flush()

        if payload.username is not None and payload.password is not None:
            username = payload.username.strip()
            user = db.query(User).filter(User.username == username).first()
            if user is not None:
                raise exc.IntegrityError(
                    statement="users.username",
                    params=None,
                    orig=Exception("UNIQUE constraint failed: users.username"),
                )

            user = User(
                username=username,
                password_hash=hash_password(payload.password),
                role=Role.FACULTY,
                faculty_id=faculty.id,
                student_id=None,
                department_id=department_id,
            )
            db.add(user)
            db.flush()

        db.commit()
        db.refresh(faculty)
        return _serialize_faculty(db, faculty)
    except exc.IntegrityError as exc_obj:
        db.rollback()
        raise _duplicate_error_from_integrity(exc_obj)


@router.get("", response_model=list[FacultyResponse])
def list_faculty(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    faculty_rows = db.query(Faculty).filter(Faculty.department_id == department_id).order_by(Faculty.created_at.desc()).all()
    return [_serialize_faculty(db, faculty) for faculty in faculty_rows]


@router.get("/{faculty_id}", response_model=FacultyResponse)
def get_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if faculty is None or faculty.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")
    return _serialize_faculty(db, faculty)


@router.put("/{faculty_id}", response_model=FacultyResponse)
def update_faculty(
    faculty_id: int,
    payload: FacultyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if faculty is None or faculty.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _serialize_faculty(db, faculty)

    for field in ("name", "faculty_code", "email"):
        if field in updates and updates[field] is not None:
            setattr(faculty, field, updates[field].strip())

    try:
        db.commit()
        db.refresh(faculty)
        return _serialize_faculty(db, faculty)
    except exc.IntegrityError as exc_obj:
        db.rollback()
        raise _duplicate_error_from_integrity(exc_obj)


@router.delete("/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if faculty is None or faculty.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")

    linked_user = db.query(User).filter(User.faculty_id == faculty.id).first()
    try:
        if linked_user is not None:
            db.delete(linked_user)
        db.delete(faculty)
        db.commit()
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete faculty: they are still assigned to subjects, timetable entries, or availability records.",
        )
