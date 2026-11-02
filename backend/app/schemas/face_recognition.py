from typing import Optional

from pydantic import BaseModel, Field


class RecognitionResult(BaseModel):
    matched: bool
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    confidence: float = Field(default=0.0)
    message: str
