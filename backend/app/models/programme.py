from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.database import Base


class Programme(Base):
    __tablename__ = "programmes"
    __table_args__ = (
        UniqueConstraint("department_id", "name", name="uq_department_programme"),
    )

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    department = relationship("Department", back_populates="programmes")
    academic_years = relationship(
        "AcademicYear",
        back_populates="programme",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
