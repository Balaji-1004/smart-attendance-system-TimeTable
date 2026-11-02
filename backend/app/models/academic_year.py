from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.database import Base


class AcademicYear(Base):
    __tablename__ = "academic_years"
    __table_args__ = (
        UniqueConstraint("department_id", "name", name="uq_department_year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    department = relationship("Department", back_populates="academic_years")

    # One academic year has many students
    students = relationship("Student", back_populates="academic_year")

    # One academic year can have many subjects
    subjects = relationship("Subject", back_populates="academic_year")

    # Timetable entries for this academic year
    timetable_entries = relationship("TimetableEntry", back_populates="academic_year")

    attendance_sessions = relationship("AttendanceSession", back_populates="academic_year")
    attendance_records = relationship("Attendance", back_populates="academic_year")
