from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database.database import Base
from app.models.enums import SessionStatus


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id = Column(Integer, primary_key=True, index=True)
    timetable_entry_id = Column(Integer, ForeignKey("timetable_entries.id"), nullable=False)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(SQLEnum(SessionStatus, name="session_status"), nullable=False, default=SessionStatus.OPEN)

    timetable_entry = relationship("TimetableEntry", back_populates="attendance_sessions")
    faculty = relationship("Faculty", back_populates="attendance_sessions")
    subject = relationship("Subject", back_populates="attendance_sessions")
    academic_year = relationship("AcademicYear", back_populates="attendance_sessions")

    attendance_records = relationship("Attendance", back_populates="attendance_session")
