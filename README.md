# Smart Attendance System

A full-stack student attendance system for the **Computer Science department**, which contains the **MCA** and **MTech** programmes. The backend uses FastAPI, SQLAlchemy, and SQLite; the frontend uses React and Vite. Features include department-scoped academic management, timetable generation, attendance sessions, reports, student self-service, and student face recognition. Faculty face registration is supported, but faculty face recognition is not implemented.

## Prerequisites

- Python compatible with the versions pinned in `backend/requirements.txt`.
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

Set a private `JWT_SECRET_KEY` in `backend/.env`; never commit real credentials. The example database URL is `sqlite:///./smart_attendance.db`, relative to the backend working directory. Initialize the schema and start the API:

```powershell
python -m app.database.init_db
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`init_db` imports the models and calls SQLAlchemy `Base.metadata.create_all`. It creates missing tables, but it does not upgrade existing tables and is not a schema migration system.

### Initial department and HOD

For a new database, create the department and its first HOD. `create_department.py` also creates a same-named programme; pass an empty `--years` value if you plan to add the MCA and MTech programmes separately:

```powershell
python scripts/create_department.py --name "Computer Science" --hod-username <hod-username> --years ""
```

If `--hod-password` is omitted, the script generates a password and prints it once. Sign in as that HOD and create the MCA and MTech programmes, then create `1st Year` and `2nd Year` in each programme from the programme/academic-year management UI or API. The unused empty `Computer Science` programme can be deleted after setup. To add an HOD and years to an already existing **empty** department, use `--use-existing`; it refuses populated departments.

`scripts/create_hod.py` is a legacy interactive utility that does not assign a department. Department-scoped login requires a department assignment, so use `create_department.py` for initial setup.

The one-time `scripts/migrate_programmes.py` is for the known legacy database baseline and validates its expected face-embedding hash before applying changes. It is not a generic fresh-database initializer. See [test_results.md](./docs/test_results.md) for the current database verification status.

## Frontend setup

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server uses `http://localhost:5173`; the frontend API client targets `http://localhost:8000`.

## Roles

- **HOD**: manages programmes, academic years, students, faculty, subjects, labs, faculty availability, timetables, attendance sessions, and reports for the HOD's department.
- **FACULTY**: accesses department-scoped read views, their own timetable and attendance sessions, relevant reports, and can register their own face embedding.
- **STUDENT**: accesses their profile, academic-year timetable, and attendance summary/history.

Backend dependencies enforce role and ownership checks. Department ownership is derived from the authenticated user's database-backed profile.

## Main workflows

1. **Programme and academic data**: the department contains MCA and MTech; each has its own `1st Year` and `2nd Year`. Years, students, faculty, subjects, and labs are department-scoped.
2. **Timetable generation and editing**: an HOD generates a timetable for an academic year. The deterministic generator tries lab blocks before theory and uses recursive backtracking up to 50,000 validator calls; results include feasibility warnings and unscheduled items.
3. **Attendance**: HOD or faculty starts a session from a timetable entry, marks students present manually or requests a recognition result, and closes the session. Closing adds explicit `ABSENT` rows for enrolled students not already marked in that session.
4. **Face registration and recognition**: an HOD can register a student's face; HOD can register faculty faces and faculty can register their own. Attendance recognition matches only student faces in the session's academic year. Recognition does not save attendance; manual review/marking remains the attendance workflow.
5. **Dashboards and reports**: dashboard and report data are filtered according to role, department, and faculty/student relationships.

## Scripts

- `scripts/migrate_add_departments.py` and `scripts/migrate_add_department_ownership.py`: legacy SQLite schema/ownership migrations; inspect their baseline assumptions and backups before use.
- `scripts/migrate_programmes.py`: dry-run by default; `--apply` migrates the supported legacy schema to programmes, preserves student face data, and refuses if the expected embedding hash differs.
- `scripts/create_department.py`: creates a department, a same-named programme, academic years, and HOD, or adds years/HOD to an existing empty department with `--use-existing`.
- `scripts/create_hod.py`: legacy HOD utility; does not assign a department.
- `scripts/seed_mca_real.py`: idempotently adds the supplied MCA faculty/users and subjects, checks capacity, and regenerates the two MCA timetables.
- `scripts/seed_mtech_demo.py`: idempotently adds MTech demo faculty/users, labs, subjects, and students and generates the two MTech timetables. It checks the configured database path and requires the expected backup for the real DB.
- `scripts/rename_departments.py`: legacy department rename/inventory utility; dry run is the default.
- `scripts/test_validator.py`: validator and feasibility checks, including candidate-aware faculty limits and edit exclusions.
- `scripts/test_backtracking.py`: full-year placement, greedy comparison, impossible case, deterministic output, uniqueness, and clean regeneration checks.
- `scripts/test_department_isolation.py`: cross-department authorization, lab-capacity, attendance, and dashboard isolation checks.
- `scripts/test_full_flow.py`: attendance session, close/backfill, student portal, and role checks.
- `scripts/test_programmes.py`: programme CRUD/scoping, academic-year programme ownership, and faculty face-registration checks.
- `scripts/test_generator_loader.py` and `scripts/test_generator_run.py`: block-loader and regeneration checks.
- `scripts/test_face_libs.py`: optional MediaPipe/DeepFace smoke test; it may download its detector model and does not use the application database.

All database-writing `test_*.py` scripts refuse database filenames other than `smart_attendance.test_copy.db`. Before each test run, create a fresh disposable copy in `backend/` and set `DATABASE_URL` to that copy from the backend working directory. The face-library smoke test does not use the database.

See [`docs/`](./docs/) for the schema, architecture, algorithm, department rules, API inventory, face-recognition notes, and test evidence.
