# Smart Attendance System

A full-stack attendance tracking project with a FastAPI backend and a Vite React frontend.

## Backend setup

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on http://localhost:5173 and the backend API runs on http://localhost:8000.
