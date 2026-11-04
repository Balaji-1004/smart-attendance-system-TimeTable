from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.academic_years import router as academic_years_router
from app.routers.attendance_sessions import router as attendance_sessions_router
from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.faculty import router as faculty_router
from app.routers.faculty_availability import router as faculty_availability_router
from app.routers.face_data import router as face_data_router
from app.routers.labs import router as labs_router
from app.routers.reports import router as reports_router
from app.routers.students import router as students_router
from app.routers.subjects import router as subjects_router
from app.routers.timetable import router as timetable_router

app = FastAPI(title="Smart Attendance System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(attendance_sessions_router)
app.include_router(academic_years_router)
app.include_router(students_router)
app.include_router(face_data_router)
app.include_router(faculty_router)
app.include_router(subjects_router)
app.include_router(labs_router)
app.include_router(faculty_availability_router)
app.include_router(timetable_router)
app.include_router(reports_router)
app.include_router(dashboard_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
