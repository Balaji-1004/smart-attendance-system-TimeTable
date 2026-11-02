from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database.database import Base
from app.models.enums import AttendanceStatus


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("attendance_session_id", "student_id", name="uq_session_student"),
    )

    id = Column(Integer, primary_key=True, index=True)
    attendance_session_id = Column(Integer, ForeignKey("attendance_sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    date = Column(Date, nullable=False)
    time = Column(DateTime, nullable=False)
    status = Column(SQLEnum(AttendanceStatus, name="attendance_status"), nullable=False)
    timetable_entry_id = Column(Integer, ForeignKey("timetable_entries.id"), nullable=False)

    attendance_session = relationship("AttendanceSession", back_populates="attendance_records")
    student = relationship("Student", back_populates="attendance_records")
    subject = relationship("Subject", back_populates="attendance_records")
    faculty = relationship("Faculty", back_populates="attendance_records")
    academic_year = relationship("AcademicYear", back_populates="attendance_records")
    timetable_entry = relationship("TimetableEntry", back_populates="attendance_records")
