from pydantic import BaseModel


class FaceRegistrationResponse(BaseModel):
    student_id: int
    face_registered: bool
    message: str


class FaceRegistrationStatusResponse(BaseModel):
    student_id: int
    face_registered: bool
    face_data_exists: bool
