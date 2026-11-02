from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import DateTime
from datetime import datetime
from sqlalchemy import String
from sqlalchemy import Boolean

from app.database.database import Base
from app.models.enums import WeekDay, Period
from sqlalchemy import Enum as SQLEnum


class FacultyAvailability(Base):
    __tablename__ = "faculty_availability"
    __table_args__ = (UniqueConstraint("faculty_id", "day", "period", name="uq_faculty_day_period"),)

    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)
    day = Column(SQLEnum(WeekDay, name="weekday"), nullable=False)
    period = Column(SQLEnum(Period, name="period"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    faculty = relationship("Faculty", back_populates="unavailable_slots")
