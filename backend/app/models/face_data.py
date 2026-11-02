from datetime import datetime

from sqlalchemy import Column, Integer, LargeBinary, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database.database import Base


class FaceData(Base):
    __tablename__ = "face_data"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, unique=True)
    face_embedding = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="face_data", uselist=False)
