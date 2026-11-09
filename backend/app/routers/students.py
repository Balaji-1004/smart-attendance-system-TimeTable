from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.core.security import get_user_department_id, hash_password, require_role
from app.database.database import get_db
from app.models import AcademicYear, Student, User
from app.models.user import Role
from app.schemas.student import StudentCreate, StudentResponse, StudentUpdate

router = APIRouter(prefix="/students", tags=["students"])


def _duplicate_error_from_integrity(exc_obj: exc.IntegrityError) -> HTTPException:
    message = str(exc_obj.orig).lower()
    if "students.roll_number" in message:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A student with this roll number already exists.")
    if "students.email" in message:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A student with this email already exists.")
    if "users.username" in message:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this username already exists.")
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate record found.")


@router.post("", response_model=StudentResponse)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    academic_year = db.query(AcademicYear).filter(AcademicYear.id == payload.academic_year_id).first()
    if academic_year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
    if academic_year.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")

    student = Student(
        roll_number=payload.roll_number.strip(),
        name=payload.name.strip(),
        email=payload.email.strip(),
        academic_year_id=payload.academic_year_id,
        department_id=department_id,
        user_id=None,
        face_registered=False,
    )

    try:
        db.add(student)
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
                role=Role.STUDENT,
                student_id=student.id,
                faculty_id=None,
                department_id=department_id,
            )
            db.add(user)
            db.flush()
            student.user_id = user.id

        db.commit()
        db.refresh(student)
        return student
    except exc.IntegrityError as exc_obj:
        db.rollback()
        raise _duplicate_error_from_integrity(exc_obj)


@router.get("", response_model=list[StudentResponse])
def list_students(
    academic_year_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    query = db.query(Student)
    department_id = get_user_department_id(db, current_user)
    if academic_year_id is not None:
        query = query.filter(Student.academic_year_id == academic_year_id, Student.department_id == department_id)
    else:
        query = query.filter(Student.department_id == department_id)
    return query.order_by(Student.created_at.desc()).all()


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None or student.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None or student.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return student

    if "academic_year_id" in updates and updates["academic_year_id"] is not None:
        academic_year = db.query(AcademicYear).filter(AcademicYear.id == updates["academic_year_id"]).first()
        if academic_year is None or academic_year.department_id != department_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found")
        student.academic_year_id = updates["academic_year_id"]
        student.department_id = department_id

    for field in ("roll_number", "name", "email"):
        if field in updates and updates[field] is not None:
            setattr(student, field, updates[field].strip())

    try:
        db.commit()
        db.refresh(student)
        return student
    except exc.IntegrityError as exc_obj:
        db.rollback()
        raise _duplicate_error_from_integrity(exc_obj)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD")),
):
    department_id = get_user_department_id(db, current_user)
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None or student.department_id != department_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    linked_user = None
    if student.user_id is not None:
        linked_user = db.query(User).filter(User.id == student.user_id).first()
        if linked_user is not None:
            linked_user.student_id = None
            student.user_id = None

    db.delete(student)
    if linked_user is not None:
        db.delete(linked_user)

    db.commit()
