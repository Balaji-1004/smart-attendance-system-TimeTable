import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database.database import Base


class Role(enum.Enum):
    HOD = "HOD"
    FACULTY = "FACULTY"
    STUDENT = "STUDENT"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(SQLEnum(Role, name="user_role"), nullable=False)

    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    department = relationship("Department", back_populates="users")
    faculty = relationship("Faculty", foreign_keys=[faculty_id], uselist=False)
    student = relationship("Student", foreign_keys=[student_id], uselist=False)
