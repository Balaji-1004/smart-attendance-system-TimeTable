# Architecture

## Layers and folders

```text
backend/
  app/
    core/       settings, JWT/password helpers, current-user and role dependencies
    database/   SQLAlchemy engine/session and create_all initializer
    models/     SQLAlchemy entities and enums
    schemas/    Pydantic request/response types
    routers/    FastAPI endpoints and HTTP authorization
    services/   timetable generation/validation, face processing, dashboard and student logic
  scripts/      migrations, setup/seed utilities, inspection and regression scripts
frontend/
  src/
    components/ shared UI and timetable components
    context/    authentication state
    pages/      dashboards, management, attendance, and reports
    services/   Axios API client
    styles/     application theme
```

The programme structure is one department with separate MCA and MTech programmes. Each programme has its own academic years; academic-year names such as `1st Year` may repeat across programmes.

`backend/app/main.py` creates the FastAPI application, installs CORS for `http://localhost:5173`, and registers routers. `backend/app/database/database.py` creates the SQLAlchemy engine from `DATABASE_URL` and provides request-scoped sessions. `backend/app/database/init_db.py` imports models and calls `Base.metadata.create_all`; it is not an Alembic migration.

## Login request flow

1. `POST /auth/login` checks the submitted username and password against `users` using the configured Passlib bcrypt context.
2. The route derives the department from the database-backed profile: HOD's `User.department_id`, faculty's linked `Faculty.department_id`, or student's linked `Student.department_id`.
3. It creates a signed JWT carrying the user id, username, role, derived department id, and linked faculty/student ids, then returns the token and identity fields.
4. Protected requests decode the bearer token, reload the `User` by token subject, and use that database record for role and ownership checks. Department ownership is resolved from the corresponding profile, not from a client-supplied department id.

## Timetable generation flow

1. `POST /timetable/generate` accepts an academic-year id and requires HOD.
2. The router confirms the year belongs to the HOD's department.
3. `generate_timetable` computes feasibility warnings, removes existing entries for that year, loads subject blocks, and invokes deterministic recursive backtracking. LAB blocks are first; theory blocks follow. `MAX_NODES` bounds validator calls at 50,000, and a best partial schedule is returned if search cannot finish.
4. Validators check conflicts, availability, daily/weekly faculty limits, and department-scoped lab capacity against existing and tentatively placed entries. The service persists the replacement entries and returns placed count, unscheduled items, and warnings.

`run_generation(..., use_backtracking=False)` remains available for deterministic greedy first-fit comparison. See [timetable_algorithm.md](./timetable_algorithm.md).

## Attendance session flow

1. HOD or faculty submits a timetable-entry id to `POST /attendance-sessions`.
2. The route verifies department ownership and, for faculty, ownership of the timetable entry. It rejects a second open session for the same entry/date.
3. Present marks are added through `POST /attendance-sessions/{session_id}/mark`; duplicate marks are rejected in application logic and by a database unique constraint.
4. Optional recognition uses `POST /attendance-sessions/{session_id}/recognize` with a multipart image file and returns a candidate; it does not mark attendance automatically.
5. `PUT /attendance-sessions/{session_id}/close` closes the session and inserts explicit ABSENT rows for enrolled students without an attendance row for that session.

## Face workflows

Student registration is `POST /students/{student_id}/face-registration` (HOD). Faculty registration is available to HOD at `POST /faculty/{faculty_id}/face-registration` and to a faculty member for their own profile at `POST /faculty/me/face-registration`. Both registration paths use the shared face service and store one embedding per profile in separate `face_data` and `faculty_face_data` tables.

Attendance recognition currently operates on student embeddings only. The session endpoint detects exactly one face, compares its embedding with registered students in that session's academic year, and returns a result for faculty review. Recognition does not save attendance. See [face_recognition.md](./face_recognition.md).
