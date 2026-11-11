from pydantic import BaseModel


class FacultyFaceRegistrationResponse(BaseModel):
    faculty_id: int
    face_registered: bool
    message: str


class FacultyFaceRegistrationStatusResponse(BaseModel):
    faculty_id: int
    face_registered: bool
    face_data_exists: bool
