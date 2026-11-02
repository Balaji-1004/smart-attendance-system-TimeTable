from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StudentCreate(BaseModel):
    roll_number: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    academic_year_id: int
    username: str | None = None
    password: str | None = None

    @model_validator(mode="after")
    def validate_login_fields(self):
        has_username = self.username is not None
        has_password = self.password is not None
        if has_username != has_password:
            raise ValueError("Both username and password are required to create a login, or neither.")
        return self


class StudentUpdate(BaseModel):
    roll_number: str | None = None
    name: str | None = None
    email: str | None = None
    academic_year_id: int | None = None


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    roll_number: str
    name: str
    email: str
    academic_year_id: int
    department_id: int
    user_id: int | None
    face_registered: bool
    created_at: datetime
    updated_at: datetime
