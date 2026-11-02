from app.database.database import Base
from sqlalchemy import Column, Integer, String
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship


class Lab(Base):
    __tablename__ = "labs"

    id = Column(Integer, primary_key=True, index=True)
    lab_code = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    # intentionally minimal per project rules

    # Timetable entries that use this lab
    timetable_entries = relationship("TimetableEntry", back_populates="lab")
