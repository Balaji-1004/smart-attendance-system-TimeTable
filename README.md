# Smart Attendance System

A full-stack student attendance system for the **MCA** and **MTech** programmes. The application uses FastAPI, SQLAlchemy, and SQLite on the backend, with React and Vite on the frontend. It provides department-scoped academic management, timetable generation, attendance sessions, reports, and single-face recognition.

## Prerequisites

- Python version compatible with the pinned packages in `backend/requirements.txt` (the face-recognition dependencies currently pin TensorFlow 2.15).
- Node.js and npm.

## Backend setup

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set a private `JWT_SECRET_KEY` in `backend/.env`; do not commit real credentials. The example database URL is `sqlite:///./smart_attendance.db`, relative to the backend working directory. Then initialize the database schema and start the API:

```powershell
python -m app.database.init_db
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`init_db` calls SQLAlchemy `Base.metadata.create_all`; it creates missing tables, but it is not a schema migration system and does not upgrade existing tables.

### Initial department and HOD setup

For a new department, create its department row, academic years, and HOD in one script operation:

```powershell
python scripts/create_department.py --name MCA --hod-username <mca-hod-username>
python scripts/create_department.py --name MTech --hod-username <mtech-hod-username>
```

Supply `--hod-password` only through a suitably private process; if omitted, the script generates a password and prints it once. Use names and usernames that are not already present. If adding a HOD and years to an existing **empty** department, use `--use-existing`:

```powershell
python scripts/create_department.py --name <existing-department> --hod-username <username> --use-existing
```

The script refuses to populate a non-empty existing department. `scripts/create_hod.py` is a legacy interactive utility that creates an HOD account **without** assigning `department_id`; department-scoped routes require a department assignment, so prefer `create_department.py` for normal setup.

## Frontend setup

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server uses `http://localhost:5173`; the frontend API client currently targets `http://localhost:8000`.

## Roles

- **HOD**: manages the authenticated department's academic years, students, faculty, subjects, labs, faculty availability, timetable, and attendance/report views.
- **FACULTY**: works with their own attendance sessions and timetable entries, and can access department-scoped read views and reports limited to their assigned subjects where implemented.
- **STUDENT**: accesses their own profile, academic-year timetable, and attendance summary/history.

Authorization and department ownership are checked by the backend. A department identifier supplied in a request or JWT claim is not the source of ownership.

## Main workflows

1. **Department setup and academic data**: an HOD's department contains its academic years, students, faculty, subjects, and labs. Student/faculty creation can optionally create a linked login in the same transaction.
2. **Timetable generation and editing**: the HOD generates a timetable for an academic year. Lab blocks are placed before theory periods, with feasibility warnings and unscheduled items returned in the response. HODs and faculty members can edit/delete entries subject to backend checks.
3. **Attendance**: HODs and faculty members start a session from a timetable entry, mark students present manually or request recognition from a one-face image, and close the session. Closing backfills explicit `ABSENT` records for unmarked students in that academic year.
4. **Face recognition**: an HOD registers or replaces one student's face embedding. Recognition is scoped to students in the attendance session's academic year. A failed or uncertain recognition can be handled through the manual attendance workflow.
5. **Dashboards and reports**: dashboard and report data are filtered according to the caller's role and department/faculty/student relationship.

## Scripts

- `scripts/migrate_add_departments.py`: legacy SQLite migration that creates/backfills department ownership and makes a backup. Review its hard-coded legacy department names before use.
- `scripts/migrate_add_department_ownership.py`: adds/backfills ownership columns transactionally and verifies the face-embedding hash; it also assumes the legacy department name `Computer Science`.
- `scripts/create_department.py`: creates a department, years, and HOD, or adds years/HOD to an existing empty department with `--use-existing`.
- `scripts/seed_mtech_demo.py`: seeds MTech demo records and generates its timetables. It requires the real backend DB and backup and changes data; do not run casually.
- `scripts/rename_departments.py`: prints a read-only inventory by default; `--apply` changes department names in a transaction.
- `scripts/test_department_isolation.py`: department-boundary API checks; refuses unless `DATABASE_URL` names `smart_attendance.test_copy.db`.
- `scripts/test_full_flow.py`: attendance/student portal/API flow checks; refuses unless the configured SQLite DB is `backend/smart_attendance.test_copy.db`.
- `scripts/test_validator.py`: exercises timetable validator/feasibility checks. It uses the configured database session and writes fixture rows; it does **not** enforce a test-copy filename.
- `scripts/test_generator_loader.py` and `scripts/test_generator_run.py`: generator loader and regeneration checks. They use the configured database and write fixture/timetable rows; they do **not** enforce a test-copy filename.
- `scripts/test_face_libs.py`: optional MediaPipe/DeepFace smoke test. It uses an image if present and can download the MediaPipe model; it does not use the application DB.

For every database-writing test, first make a disposable copy named `smart_attendance.test_copy.db` and set `DATABASE_URL` to that copy from the backend directory. Only the two department/flow scripts enforce that name themselves; the older validator/generator tests must be pointed at the copy manually.

See [`docs/`](./docs/) for the schema, architecture, algorithm, department rules, API inventory, face-recognition notes, and test evidence.
