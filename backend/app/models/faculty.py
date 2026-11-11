from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class Faculty(Base):
    __tablename__ = "faculty"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    face_registered = Column(Boolean, default=False, nullable=False)
    name = Column(String, nullable=False)
    faculty_code = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    department = relationship("Department", back_populates="faculty")
    subjects = relationship("Subject", back_populates="faculty")
    unavailable_slots = relationship("FacultyAvailability", back_populates="faculty")
    timetable_entries = relationship("TimetableEntry", back_populates="faculty")
    attendance_sessions = relationship("AttendanceSession", back_populates="faculty")
    attendance_records = relationship("Attendance", back_populates="faculty")
    face_data = relationship("FacultyFaceData", back_populates="faculty", uselist=False, cascade="all, delete-orphan")
