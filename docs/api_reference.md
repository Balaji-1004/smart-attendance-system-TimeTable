# API reference

All paths are relative to the FastAPI origin (default `http://localhost:8000`). Protected endpoints use a bearer JWT. Role names are `HOD`, `FACULTY`, and `STUDENT`. Unsupported roles receive 403; cross-department resource lookups generally return 404.

| Method | Path | Allowed roles | Purpose |
|---|---|---|---|
| GET | `/health` | Public | Return service health status. |
| POST | `/auth/login` | Public | Validate credentials and return an access token and linked identity fields. |
| GET | `/departments/me` | HOD, FACULTY, STUDENT | Return the authenticated user's database-derived department. |
| POST | `/academic-years` | HOD | Create an academic year in the caller's department. |
| GET | `/academic-years` | HOD, FACULTY | List academic years in the caller's department. |
| GET | `/academic-years/{academic_year_id}` | HOD, FACULTY | Read one department-owned academic year. |
| PUT | `/academic-years/{academic_year_id}` | HOD | Update a department-owned academic year. |
| DELETE | `/academic-years/{academic_year_id}` | HOD | Delete a department-owned academic year if no dependent rows prevent it. |
| POST | `/students` | HOD | Create a student, optionally with a linked student login. |
| GET | `/students?academic_year_id=` | HOD, FACULTY | List department students, optionally filtering by academic year. |
| GET | `/students/{student_id}` | HOD | Read a department-owned student. |
| PUT | `/students/{student_id}` | HOD | Update a department-owned student's profile/year. |
| DELETE | `/students/{student_id}` | HOD | Delete a department-owned student and its linked login when present. |
| POST | `/students/{student_id}/face-registration` | HOD | Register or replace one face embedding from a multipart image. |
| GET | `/students/{student_id}/face-registration-status` | HOD | Read face-registration status for a department-owned student. |
| GET | `/me/profile` | STUDENT | Read the authenticated student's profile, academic year, department, and face flag. |
| GET | `/me/timetable` | STUDENT | Read timetable entries for the authenticated student's academic year. |
| GET | `/me/attendance/summary` | STUDENT | Read per-subject and overall attendance percentages. |
| GET | `/me/attendance/history?subject_id=` | STUDENT | Read the authenticated student's newest-first attendance history, optionally filtered by subject. |
| POST | `/faculty` | HOD | Create faculty and optionally a linked faculty login. |
| GET | `/faculty` | HOD | List faculty in the caller's department. |
| GET | `/faculty/{faculty_id}` | HOD | Read a department-owned faculty record. |
| PUT | `/faculty/{faculty_id}` | HOD | Update a department-owned faculty record. |
| DELETE | `/faculty/{faculty_id}` | HOD | Delete a department-owned faculty record if it has no blocking assignments. |
| POST | `/subjects` | HOD | Create a subject whose year and faculty belong to the caller's department. |
| GET | `/subjects?academic_year_id=` | HOD | List department subjects, optionally filtered by academic year. |
| GET | `/subjects/{subject_id}` | HOD | Read a department-owned subject. |
| PUT | `/subjects/{subject_id}` | HOD | Update a department-owned subject, year, or faculty assignment. |
| DELETE | `/subjects/{subject_id}` | HOD | Delete a subject when no dependent schedule/attendance rows block deletion. |
| POST | `/labs` | HOD | Create a lab in the caller's department. |
| GET | `/labs` | HOD, FACULTY | List labs in the caller's department. |
| GET | `/labs/{lab_id}` | HOD, FACULTY | Read a department-owned lab. |
| PUT | `/labs/{lab_id}` | HOD | Update a department-owned lab. |
| DELETE | `/labs/{lab_id}` | HOD | Delete a lab when no timetable entries block deletion. |
| POST | `/faculty-availability` | HOD | Mark a department faculty member unavailable for a weekday/period. |
| GET | `/faculty-availability?faculty_id=` | HOD | List department availability rows, optionally for one faculty member. |
| DELETE | `/faculty-availability/{availability_id}` | HOD | Delete a department-owned availability row. |
| POST | `/timetable/generate` | HOD | Regenerate a department academic year's timetable. Body: `academic_year_id`. |
| GET | `/timetable/year/{year_id}` | HOD, FACULTY | List entries for a department-owned academic year. |
| GET | `/timetable/faculty/{faculty_id}` | HOD, FACULTY | List a department faculty timetable; faculty may request only their own. |
| GET | `/timetable/department` | HOD | List all timetable entries for the caller's department. |
| PUT | `/timetable/{entry_id}` | HOD, FACULTY | Move an entry after validation; faculty may edit only their own entries. |
| DELETE | `/timetable/{entry_id}` | HOD, FACULTY | Delete an entry; faculty may delete only their own entries. |
| POST | `/attendance-sessions` | HOD, FACULTY | Start today's session for a timetable entry. Body: `timetable_entry_id`. |
| POST | `/attendance-sessions/{session_id}/mark` | HOD, FACULTY | Mark one student PRESENT in an open session. Body: `student_id`. |
| POST | `/attendance-sessions/{session_id}/recognize` | HOD, FACULTY | Return a recognition candidate from a multipart `file`; does not mark attendance. |
| PUT | `/attendance-sessions/{session_id}/close` | HOD, FACULTY | Close an open session and backfill ABSENT rows for unmarked students. |
| GET | `/attendance-sessions?date=&status=&academic_year_id=` | HOD, FACULTY | List department sessions for HOD or the caller's own sessions for faculty, with optional filters. |
| GET | `/attendance-sessions/{session_id}` | HOD, FACULTY | Read a session if department and, for faculty, ownership checks pass. |
| GET | `/reports/attendance/daily?date=&academic_year_id=&subject_id=` | HOD, FACULTY | Read daily attendance rows; faculty results are limited to assigned subjects. |
| GET | `/reports/attendance/subject/{subject_id}` | HOD, FACULTY | Read per-student attendance totals and percentages for one subject. |
| GET | `/reports/attendance/student/{student_id}?subject_id=` | HOD, FACULTY | Read department student attendance history, subject-filtered optionally. |
| GET | `/reports/attendance/class-summary/{academic_year_id}?faculty_id=` | HOD, FACULTY | Read subject summaries for a year; faculty sees their assigned subjects. |
| GET | `/dashboard/hod` | HOD | Read department-specific counts, warnings, attendance, and session summaries. |
| GET | `/dashboard/faculty` | FACULTY | Read faculty-specific counts, today's sessions, and upcoming entries. |
| GET | `/dashboard/student` | STUDENT | Read the legacy student dashboard summary for the authenticated student. |

Schemas are defined under `backend/app/schemas/`; route-level role dependencies and additional ownership checks are in `backend/app/routers/`.
