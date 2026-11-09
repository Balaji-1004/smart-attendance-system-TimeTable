from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    roll_number = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)

    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)

    # Optional link to user (may be null until a user is created)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    face_registered = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    academic_year = relationship("AcademicYear", back_populates="students")
    department = relationship("Department", back_populates="students")

    attendance_records = relationship("Attendance", back_populates="student")
    face_data = relationship("FaceData", back_populates="student", uselist=False)
