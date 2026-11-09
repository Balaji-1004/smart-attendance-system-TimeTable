from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = Field(default="bearer")
    role: str
    username: str
    department_id: int
    faculty_id: Optional[int] = None
    student_id: Optional[int] = None
