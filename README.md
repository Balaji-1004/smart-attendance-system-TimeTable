# Student Smart Attendance System

A full-stack attendance application for managing academic timetables and student attendance. It combines a FastAPI backend, a React/Vite frontend, SQLite storage, and face recognition to support HOD, Faculty, and Student workflows.

## Features

- Timetable generation using hand-written backtracking.
- Face-recognition-assisted attendance sessions.
- Role-based access for HOD, Faculty, and Student.
- Attendance reports and role-specific dashboards.

## Tech stack

- Backend: Python, FastAPI, SQLAlchemy, SQLite.
- Frontend: React, Vite, Axios.
- Face recognition: OpenCV, MediaPipe, DeepFace.

## Prerequisites

- Python 3.9-3.11 (for TensorFlow 2.15 and MediaPipe 0.10.14).
- Node.js 20.19+ or 22.12+, with npm.

## Backend setup

From the repository root, create and activate a virtual environment, then install dependencies:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and replace `JWT_SECRET_KEY` with a private secret. Initialize the database and create an HOD login:

```powershell
python -m app.database.init_db
python scripts/create_hod.py
```

`create_hod.py` prompts for credentials but is a legacy helper that does not assign a department. For a fresh, department-scoped setup, use `python scripts/create_department.py --name "Computer Science" --hod-username <username> --years ""` instead; it creates the department and its initial HOD.

To run the API:

```powershell
uvicorn app.main:app --reload
```

Optional demo reset:

```powershell
python scripts/reset_for_demo.py
```

**Warning: `reset_for_demo.py` wipes and replaces the application's database data and prints randomly generated demo credentials. Run it only against a disposable database.**

## Frontend setup

In another terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The frontend uses `VITE_API_URL` for the backend address; it defaults to `http://localhost:8000`.

## Face recognition notes

The MediaPipe face-detection model downloads automatically on its first use. The YuNet `.onnx` model is only needed by `backend/scripts/calibrate_group_photo.py` and must be downloaded manually into `backend/scripts/models/`.

## Known limitations

`MATCH_THRESHOLD = 0.58` has been checked for different-person separation (approximately `0.39` in the tested data), but it has **not** been validated for same-person captures under different angles or lighting. See [docs/testing_notes_phase10.md](./docs/testing_notes_phase10.md).

## Screenshots

- TODO: Add a timetable grid screenshot.
- TODO: Add an attendance session screenshot.
- TODO: Add an HOD dashboard screenshot.

## Project structure

```text
backend/
  app/          FastAPI application, models, schemas, and services
  scripts/      Setup, maintenance, calibration, and test scripts
  requirements.txt
frontend/
  src/          React pages, components, context, and API client
  package.json
docs/           Architecture, API, face-recognition, and test documentation
```
