from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.core.security import get_user_department_id, hash_password, require_role
from app.database.database import get_db
from app.models import Faculty, FacultyFaceData, User
from app.models.user import Role
from app.schemas.faculty import FacultyCreate, FacultyResponse, FacultyUpdate
from app.schemas.faculty_face_data import (
    FacultyFaceRegistrationResponse,
    FacultyFaceRegistrationStatusResponse,
)
from app.services.face_service import detect_single_face, generate_embedding, serialize_embedding

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
        "face_registered": bool(faculty.face_registered),
        "user_id": user_id,
        "created_at": faculty.created_at,
    }


def _register_faculty_face(db: Session, faculty: Faculty, file_bytes: bytes):
    detection = detect_single_face(file_bytes)
    face_count = detection.get("face_count", 0)
    if face_count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No face detected in the uploaded image.")
    if face_count > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple faces detected; please upload an image with exactly one face.",
        )

    serialized_embedding = serialize_embedding(generate_embedding(file_bytes))
    existing = db.query(FacultyFaceData).filter(FacultyFaceData.faculty_id == faculty.id).first()
    if existing is None:
        db.add(FacultyFaceData(faculty_id=faculty.id, face_embedding=serialized_embedding))
        message = "Face registration successful."
    else:
        existing.face_embedding = serialized_embedding
        message = "Face registration updated successfully."
    faculty.face_registered = True
    db.commit()
    return FacultyFaceRegistrationResponse(
        faculty_id=faculty.id,
        face_registered=True,
        message=message,
    )


@router.post("/me/face-registration", response_model=FacultyFaceRegistrationResponse)
async def register_own_faculty_face(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("FACULTY")),
):
    faculty = db.query(Faculty).filter(Faculty.id == current_user.faculty_id).first()
    if faculty is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty profile not found")
    return _register_faculty_face(db, faculty, await file.read())


@router.post("/{faculty_id}/face-registration", response_model=FacultyFaceRegistrationResponse)
async def register_faculty_face(
    faculty_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if faculty is None or faculty.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")
    return _register_faculty_face(db, faculty, await file.read())


@router.get(
    "/{faculty_id}/face-registration-status",
    response_model=FacultyFaceRegistrationStatusResponse,
)
def get_faculty_face_registration_status(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if faculty is None or faculty.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")
    face_data = db.query(FacultyFaceData).filter(FacultyFaceData.faculty_id == faculty_id).first()
    return FacultyFaceRegistrationStatusResponse(
        faculty_id=faculty_id,
        face_registered=bool(faculty.face_registered),
        face_data_exists=face_data is not None,
    )


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
