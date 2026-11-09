# Architecture

## Layers and folders

```text
backend/
  app/
    core/       settings, JWT/password helpers, current-user and role dependencies
    database/   SQLAlchemy engine/session and create_all initializer
    models/     SQLAlchemy entities and enums
    schemas/    Pydantic request/response types
    routers/    FastAPI endpoints and HTTP-level authorization
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

`backend/app/main.py` creates the FastAPI application, installs CORS for `http://localhost:5173`, and registers each router. `backend/app/database/database.py` creates the SQLAlchemy engine from `DATABASE_URL` and provides request-scoped sessions. `backend/app/database/init_db.py` imports the models and calls `Base.metadata.create_all`; it is not an Alembic migration.

## Login request flow

1. `POST /auth/login` validates the username/password against the `users` row using Passlib's bcrypt context.
2. The route derives the department from the database-backed profile: HOD's `User.department_id`, faculty's linked `Faculty.department_id`, or student's linked `Student.department_id`.
3. It creates a signed JWT carrying `sub`, username, role, department id, and linked faculty/student ids, then returns the token and those response fields.
4. Protected requests decode the bearer token, reload the `User` by token `sub`, and use the database user object for authorization. `require_role` rejects unsupported roles with 403.

## Timetable generation flow

1. `POST /timetable/generate` accepts an academic-year id and requires HOD.
2. The router confirms that the year belongs to the HOD's department.
3. `generate_timetable` computes feasibility warnings, removes the existing timetable rows for that year, loads subject blocks, and searches candidate slots. Lab blocks are searched before theory blocks.
4. The validator checks year/faculty/lab conflicts and constraints against existing and tentatively placed rows. The generator returns the placed count, unscheduled items, and warnings; its service commits regenerated entries.

The search is greedy: a candidate that passes validation is accepted immediately, and a later block does not cause earlier blocks to be moved. See [timetable_algorithm.md](./timetable_algorithm.md).

## Attendance session flow

1. HOD or faculty submits a timetable-entry id to `POST /attendance-sessions`.
2. The route verifies department ownership and, for faculty, ownership of the timetable entry. It rejects a second open session for the same entry/date.
3. Present marks are added through `POST /attendance-sessions/{session_id}/mark`; duplicate marks are rejected in application logic and guarded by a unique database constraint.
4. Optional recognition uses `POST /attendance-sessions/{session_id}/recognize` with a multipart image file and returns a recognition result; it does not mark attendance automatically.
5. `PUT /attendance-sessions/{session_id}/close` closes the session and inserts explicit ABSENT rows for enrolled students without an attendance row for that session.

## Face-recognition flow

`POST /students/{student_id}/face-registration` accepts one multipart image for an HOD-managed student. MediaPipe detects zero, one, or multiple faces; only exactly one proceeds to DeepFace embedding extraction and storage. Registering again replaces the existing single `FaceData` embedding for that student.

The recognition endpoint applies the same one-face gate, then loads registered embeddings for students in the session's academic year. It selects the highest cosine similarity and compares it with the hard-coded threshold. A match response is informational; the caller must separately mark attendance. See [face_recognition.md](./face_recognition.md) for limitations.
