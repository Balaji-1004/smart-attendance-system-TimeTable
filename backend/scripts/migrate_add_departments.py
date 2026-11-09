#!/usr/bin/env python3
import os
import secrets
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.core.security import hash_password
except Exception:
    hash_password = None

DB_PATH = BACKEND_DIR / "smart_attendance.db"
BACKUP_DIR = BACKEND_DIR


def ensure_table_columns(conn):
    tables = ["users", "faculty", "labs"]
    for table in tables:
        info = conn.execute(f"PRAGMA table_info({table})").fetchall()
        columns = {row[1] for row in info}
        if "department_id" not in columns:
            print(f"ALTER TABLE {table} ADD COLUMN department_id INTEGER")
            conn.execute(f"ALTER TABLE {table} ADD COLUMN department_id INTEGER")


def count_rows(conn):
    queries = [
        ("students", "SELECT COUNT(*) FROM students"),
        ("face_data", "SELECT COUNT(*) FROM face_data"),
        ("attendance", "SELECT COUNT(*) FROM attendance"),
        ("attendance_sessions", "SELECT COUNT(*) FROM attendance_sessions"),
        ("timetable_entries", "SELECT COUNT(*) FROM timetable_entries"),
    ]
    return {name: conn.execute(sql).fetchone()[0] for name, sql in queries}


def get_or_create_department(conn, name):
    row = conn.execute("SELECT id FROM departments WHERE name = ?", (name,)).fetchone()
    if row:
        return row[0]
    conn.execute("INSERT INTO departments (name) VALUES (?)", (name,))
    conn.commit()
    return conn.execute("SELECT id FROM departments WHERE name = ?", (name,)).fetchone()[0]


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    backup_path = BACKUP_DIR / f"smart_attendance.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"Backup created: {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        before = count_rows(conn)
        print("Row counts before migration:")
        for key, value in before.items():
            print(f"  {key}: {value}")

        ensure_table_columns(conn)

        default_department_name = "Computer Science"
        default_department_id = get_or_create_department(conn, default_department_name)

        second_department_name = "Phase7 Valid Dept"
        second_department_id = get_or_create_department(conn, second_department_name)

        conn.execute(
            "UPDATE faculty SET department_id = ? WHERE department_id IS NULL",
            (default_department_id,),
        )
        conn.execute(
            "UPDATE labs SET department_id = ? WHERE department_id IS NULL",
            (default_department_id,),
        )

        # Backfill HOD users to the department of their assigned faculty/user profile where available.
        # For existing HOD rows without a department, default them to the primary department.
        conn.execute(
            "UPDATE users SET department_id = ? WHERE role = 'HOD' AND department_id IS NULL",
            (default_department_id,),
        )

        # Faculty users inherit the department of their faculty record.
        conn.execute(
            """
            UPDATE users
            SET department_id = (
                SELECT faculty.department_id
                FROM faculty
                WHERE faculty.id = users.faculty_id
            )
            WHERE users.department_id IS NULL AND users.faculty_id IS NOT NULL
            """
        )

        # Student users inherit the department of their student record.
        conn.execute(
            """
            UPDATE users
            SET department_id = (
                SELECT students.department_id
                FROM students
                WHERE students.id = users.student_id
            )
            WHERE users.department_id IS NULL AND users.student_id IS NOT NULL
            """
        )

        # Fill any remaining null department values on users with the primary department.
        conn.execute(
            "UPDATE users SET department_id = ? WHERE department_id IS NULL",
            (default_department_id,),
        )

        # Ensure existing Department 2 has a HOD user if not already present.
        slug = "phase7-valid-dept"
        hod_username = f"hod.{slug}"
        hod = conn.execute(
            "SELECT id FROM users WHERE username = ? AND role = 'HOD'",
            (hod_username,),
        ).fetchone()
        if hod is None:
            if hash_password is None:
                raise RuntimeError("Password hashing helper is unavailable")
            password = secrets.token_urlsafe(12)
            hashed = hash_password(password)
            conn.execute(
                "INSERT INTO users (username, password_hash, role, department_id, faculty_id, student_id, created_at) VALUES (?, ?, 'HOD', ?, NULL, NULL, CURRENT_TIMESTAMP)",
                (hod_username, hashed, second_department_id),
            )
            print(f"Created HOD user: {hod_username} | password: {password}")
        else:
            conn.execute(
                "UPDATE users SET department_id = ? WHERE id = ?",
                (second_department_id, hod[0]),
            )

        conn.commit()

        after = count_rows(conn)
        print("Row counts after migration:")
        for key, value in after.items():
            print(f"  {key}: {value}")

        print("PRAGMA table_info(users):")
        for row in conn.execute("PRAGMA table_info(users)"):
            print(row)
        print("PRAGMA table_info(faculty):")
        for row in conn.execute("PRAGMA table_info(faculty)"):
            print(row)
        print("PRAGMA table_info(labs):")
        for row in conn.execute("PRAGMA table_info(labs)"):
            print(row)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
