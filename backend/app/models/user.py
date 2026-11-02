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
    # Store the password hash as a plain string column for now; hashing will be added later
    password_hash = Column(String, nullable=False)

    # Role of the user. Values: HOD, FACULTY, STUDENT
    role = Column(SQLEnum(Role, name="user_role"), nullable=False)

    # References to Faculty and Student tables (not created yet). No relationship() is added here.
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # NOTE: Application-level rule (not enforced here):
    #   - HOD users should have both faculty_id and student_id as NULL
    #   - FACULTY users should have faculty_id set
    #   - STUDENT users should have student_id set
    # This will be validated at the application level during the Authentication phase.

    # Relationships to faculty and student models (no cascade here).
    # These are simple one-to-one style relationships via the FK columns.
    faculty = relationship("Faculty", foreign_keys=[faculty_id], uselist=False)
    student = relationship("Student", foreign_keys=[student_id], uselist=False)
