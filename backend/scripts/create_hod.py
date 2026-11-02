import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.security import hash_password
from app.database.database import SessionLocal
from app.models import User
from app.models.user import Role


def create_hod_user():
    username = input("Enter HOD username: ").strip()
    if not username:
        raise ValueError("Username cannot be empty.")

    password = input("Enter HOD password: ")
    if not password:
        raise ValueError("Password cannot be empty.")

    db = SessionLocal()
    try:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=Role.HOD,
            faculty_id=None,
            student_id=None,
        )
        db.add(user)
        db.commit()
        print(f"HOD user '{username}' created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    create_hod_user()
