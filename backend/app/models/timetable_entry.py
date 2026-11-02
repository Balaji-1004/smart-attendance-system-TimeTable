from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum

from app.database.database import Base
from app.models.enums import WeekDay, Period


class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    __table_args__ = (
        UniqueConstraint("academic_year_id", "day", "period", name="uq_year_day_period"),
        UniqueConstraint("faculty_id", "day", "period", name="uq_faculty_day_period"),
        UniqueConstraint("lab_id", "day", "period", name="uq_lab_day_period"),
    )

    id = Column(Integer, primary_key=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)

    day = Column(SQLEnum(WeekDay, name="weekday"), nullable=False)
    period = Column(SQLEnum(Period, name="period"), nullable=False)

    lab_id = Column(Integer, ForeignKey("labs.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    academic_year = relationship("AcademicYear", back_populates="timetable_entries")
    subject = relationship("Subject", back_populates="timetable_entries")
    faculty = relationship("Faculty", back_populates="timetable_entries")
    lab = relationship("Lab", back_populates="timetable_entries")

    attendance_sessions = relationship("AttendanceSession", back_populates="timetable_entry")
    attendance_records = relationship("Attendance", back_populates="timetable_entry")
