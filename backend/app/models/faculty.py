from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.database.database import Base


class Faculty(Base):
    __tablename__ = "faculty"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    faculty_code = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    subjects = relationship("Subject", back_populates="faculty")
    unavailable_slots = relationship("FacultyAvailability", back_populates="faculty")

    # Timetable entries taught by this faculty
    timetable_entries = relationship("TimetableEntry", back_populates="faculty")

    attendance_sessions = relationship("AttendanceSession", back_populates="faculty")
    attendance_records = relationship("Attendance", back_populates="faculty")
