from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.database import get_db
from app.models import Attendance, AttendanceSession, FaceData, Student, TimetableEntry, User
from app.models.enums import AttendanceStatus, SessionStatus
from app.schemas.attendance import AttendanceResponse, MarkAttendanceRequest
from app.schemas.attendance_session import AttendanceSessionCreate, AttendanceSessionResponse
from app.schemas.face_recognition import RecognitionResult
from app.services.face_service import (
    MATCH_THRESHOLD,
    compare_embeddings,
    deserialize_embedding,
    detect_single_face,
    find_best_match,
    generate_embedding,
)

router = APIRouter(prefix="/attendance-sessions", tags=["attendance-sessions"])


def _check_ownership(session_or_entry, current_user: User):
    if current_user.role.value == "FACULTY" and session_or_entry.faculty_id != current_user.faculty_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own attendance sessions.",
        )


@router.post("", response_model=AttendanceSessionResponse)
def start_attendance_session(
    payload: AttendanceSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    entry = db.query(TimetableEntry).filter(TimetableEntry.id == payload.timetable_entry_id).first()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable entry not found")

    _check_ownership(entry, current_user)

    today = date.today()
    existing = (
        db.query(AttendanceSession)
        .filter(
            AttendanceSession.timetable_entry_id == entry.id,
            AttendanceSession.date == today,
            AttendanceSession.status == SessionStatus.OPEN,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An open session already exists for this timetable entry today (session id: {existing.id}).",
        )

    # V1 deliberately does not require today's date/time to match the entry's weekday or period.
    session = AttendanceSession(
        timetable_entry_id=entry.id,
        faculty_id=entry.faculty_id,
        subject_id=entry.subject_id,
        academic_year_id=entry.academic_year_id,
        date=today,
        start_time=datetime.utcnow(),
        end_time=None,
        status=SessionStatus.OPEN,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/mark", response_model=AttendanceResponse)
def mark_attendance(
    session_id: int,
    payload: MarkAttendanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    session = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance session not found")

    _check_ownership(session, current_user)
    if session.status == SessionStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot mark attendance on a closed session.")

    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if student.academic_year_id != session.academic_year_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student does not belong to this academic year.")

    existing = (
        db.query(Attendance)
        .filter(
            Attendance.attendance_session_id == session.id,
            Attendance.student_id == student.id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attendance has already been marked for this student in the current session.",
        )

    attendance = Attendance(
        attendance_session_id=session.id,
        student_id=student.id,
        subject_id=session.subject_id,
        faculty_id=session.faculty_id,
        academic_year_id=session.academic_year_id,
        date=session.date,
        time=datetime.utcnow(),
        status=AttendanceStatus.PRESENT,
        timetable_entry_id=session.timetable_entry_id,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


@router.post("/{session_id}/recognize", response_model=RecognitionResult)
async def recognize_student_for_session(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    session = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance session not found")

    _check_ownership(session, current_user)
    if session.status == SessionStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot recognize attendance on a closed session.")

    file_bytes = await file.read()
    detection = detect_single_face(file_bytes)
    face_count = detection.get("face_count", 0)

    if face_count == 0:
        return RecognitionResult(
            matched=False,
            student_id=None,
            student_name=None,
            confidence=0.0,
            message="No face detected in the uploaded image.",
        )
    if face_count > 1:
        return RecognitionResult(
            matched=False,
            student_id=None,
            student_name=None,
            confidence=0.0,
            message="Multiple faces detected; please upload an image with exactly one face.",
        )

    captured_embedding = generate_embedding(file_bytes)
    candidate_rows = (
        db.query(FaceData, Student)
        .join(Student, Student.id == FaceData.student_id)
        .filter(Student.academic_year_id == session.academic_year_id)
        .all()
    )

    candidates = []
    for face_data, student in candidate_rows:
        embedding = deserialize_embedding(face_data.face_embedding, dtype="float32", length=4096)
        candidates.append((student.id, embedding, student.name))

    if not candidates:
        return RecognitionResult(
            matched=False,
            student_id=None,
            student_name=None,
            confidence=0.0,
            message="No confident match found. Please try again or mark manually.",
        )

    student_ids_and_embeddings = [(student_id, embedding) for student_id, embedding, _ in candidates]
    best_student_id, best_similarity = find_best_match(captured_embedding, student_ids_and_embeddings)
    best_student_name = next((name for student_id, _, name in candidates if student_id == best_student_id), None)

    if best_student_id is None or best_similarity < MATCH_THRESHOLD:
        return RecognitionResult(
            matched=False,
            student_id=None,
            student_name=None,
            confidence=float(best_similarity),
            message="No confident match found. Please try again or mark manually.",
        )

    return RecognitionResult(
        matched=True,
        student_id=best_student_id,
        student_name=best_student_name,
        confidence=float(best_similarity),
        message="Student recognized.",
    )


@router.put("/{session_id}/close", response_model=AttendanceSessionResponse)
def close_attendance_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    session = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance session not found")

    _check_ownership(session, current_user)
    if session.status == SessionStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session is already closed.")

    session.status = SessionStatus.CLOSED
    session.end_time = datetime.utcnow()
    enrolled_students = db.query(Student).filter(Student.academic_year_id == session.academic_year_id).all()
    existing_student_ids = {
        student_id
        for (student_id,) in db.query(Attendance.student_id)
        .filter(Attendance.attendance_session_id == session.id)
        .all()
    }
    absent_marked_count = 0
    for student in enrolled_students:
        if student.id in existing_student_ids:
            continue
        db.add(
            Attendance(
                attendance_session_id=session.id,
                student_id=student.id,
                subject_id=session.subject_id,
                faculty_id=session.faculty_id,
                academic_year_id=session.academic_year_id,
                date=session.date,
                time=datetime.utcnow(),
                status=AttendanceStatus.ABSENT,
                timetable_entry_id=session.timetable_entry_id,
            )
        )
        absent_marked_count += 1
    db.commit()
    db.refresh(session)
    return {
        **{column.name: getattr(session, column.name) for column in AttendanceSession.__table__.columns},
        "absent_marked_count": absent_marked_count,
    }


@router.get("", response_model=list[AttendanceSessionResponse])
def list_attendance_sessions(
    date_filter: Optional[date] = Query(default=None, alias="date"),
    session_status: Optional[SessionStatus] = Query(default=None, alias="status"),
    academic_year_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    query = db.query(AttendanceSession)
    if current_user.role.value == "FACULTY":
        query = query.filter(AttendanceSession.faculty_id == current_user.faculty_id)
    if date_filter is not None:
        query = query.filter(AttendanceSession.date == date_filter)
    if session_status is not None:
        query = query.filter(AttendanceSession.status == session_status)
    if academic_year_id is not None:
        query = query.filter(AttendanceSession.academic_year_id == academic_year_id)
    return query.order_by(AttendanceSession.date.desc(), AttendanceSession.start_time.desc()).all()


@router.get("/{session_id}", response_model=AttendanceSessionResponse)
def get_attendance_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("HOD", "FACULTY")),
):
    session = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance session not found")

    _check_ownership(session, current_user)
    return session
