from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.database import Base
from app.models.enums import SubjectType


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("academic_year_id", "code", name="uq_year_code"),)

    id = Column(Integer, primary_key=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    subject_type = Column(String, nullable=False)  # will store SubjectType value as string
    weekly_periods = Column(Integer, nullable=False)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    academic_year = relationship("AcademicYear", back_populates="subjects")
    faculty = relationship("Faculty", back_populates="subjects")

    # Timetable entries for this subject
    timetable_entries = relationship("TimetableEntry", back_populates="subject")

    attendance_sessions = relationship("AttendanceSession", back_populates="subject")
    attendance_records = relationship("Attendance", back_populates="subject")
