from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database.database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)

    users = relationship("User", back_populates="department")
    programmes = relationship(
        "Programme",
        back_populates="department",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    faculty = relationship("Faculty", back_populates="department")
    labs = relationship("Lab", back_populates="department")
    academic_years = relationship(
        "AcademicYear",
        back_populates="department",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    students = relationship("Student", back_populates="department")
