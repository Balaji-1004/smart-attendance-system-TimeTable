from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FacultyCreate(BaseModel):
    name: str = Field(..., min_length=1)
    faculty_code: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    username: str | None = None
    password: str | None = None

    @model_validator(mode="after")
    def validate_login_fields(self):
        has_username = self.username is not None
        has_password = self.password is not None
        if has_username != has_password:
            raise ValueError("Both username and password are required to create a login, or neither.")
        return self


class FacultyUpdate(BaseModel):
    name: str | None = None
    faculty_code: str | None = None
    email: str | None = None


class FacultyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int | None = None
    name: str
    faculty_code: str
    email: str
    face_registered: bool = False
    user_id: int | None = None
    created_at: datetime
