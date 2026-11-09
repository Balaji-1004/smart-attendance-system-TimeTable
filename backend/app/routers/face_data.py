from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import get_user_department_id, require_role
from app.database.database import get_db
from app.models import FaceData, Student, User
from app.schemas.face_data import FaceRegistrationResponse, FaceRegistrationStatusResponse
from app.services.face_service import detect_single_face, generate_embedding, serialize_embedding

router = APIRouter(prefix="/students", tags=["face-data"])


@router.post("/{student_id}/face-registration", response_model=FaceRegistrationResponse)
async def register_student_face(
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None or student.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    file_bytes = await file.read()
    detection = detect_single_face(file_bytes)
    face_count = detection.get("face_count", 0)

    if face_count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No face detected in the uploaded image.")
    if face_count > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple faces detected; please upload an image with exactly one face.",
        )

    embedding = generate_embedding(file_bytes)
    serialized_embedding = serialize_embedding(embedding)

    existing = db.query(FaceData).filter(FaceData.student_id == student_id).first()
    if existing is None:
        new_face_data = FaceData(student_id=student_id, face_embedding=serialized_embedding)
        db.add(new_face_data)
        message = "Face registration successful."
    else:
        existing.face_embedding = serialized_embedding
        message = "Face registration updated successfully."

    student.face_registered = True
    db.commit()

    return FaceRegistrationResponse(
        student_id=student_id,
        face_registered=True,
        message=message,
    )


@router.get("/{student_id}/face-registration-status", response_model=FaceRegistrationStatusResponse)
def get_student_face_registration_status(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None or student.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    face_data = db.query(FaceData).filter(FaceData.student_id == student_id).first()
    return FaceRegistrationStatusResponse(
        student_id=student_id,
        face_registered=bool(student.face_registered),
        face_data_exists=face_data is not None,
    )
