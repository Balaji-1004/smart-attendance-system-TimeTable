from app.database.database import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship


class Lab(Base):
    __tablename__ = "labs"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    lab_code = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)

    department = relationship("Department", back_populates="labs")
    timetable_entries = relationship("TimetableEntry", back_populates="lab")
