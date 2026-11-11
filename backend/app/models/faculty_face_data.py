from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary
from sqlalchemy.orm import relationship

from app.database.database import Base


class FacultyFaceData(Base):
    __tablename__ = "faculty_face_data"

    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False, unique=True)
    face_embedding = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    faculty = relationship("Faculty", back_populates="face_data", uselist=False)
