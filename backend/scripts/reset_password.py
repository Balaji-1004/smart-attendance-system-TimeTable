import argparse
import secrets
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import hash_password
from app.database.database import SessionLocal, engine
from app.models import User


def main():
    parser = argparse.ArgumentParser(description="Reset a user's password.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password")
    args = parser.parse_args()
    if args.password == "":
        parser.error("--password cannot be empty.")

    database_path = Path(engine.url.database)
    resolved_database_path = (
        database_path if database_path.is_absolute() else BACKEND_DIR / database_path
    )
    if resolved_database_path.resolve() != (BACKEND_DIR / "smart_attendance.db").resolve():
        parser.error("Refusing to reset passwords unless DATABASE_URL points to backend/smart_attendance.db.")

    password = (
        args.password
        if args.password is not None
        else secrets.token_urlsafe(16)
    )
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == args.username).first()
        if user is None:
            parser.error(f"Unknown username: {args.username}")
        user.password_hash = hash_password(password)
        db.commit()
        if args.password is None:
            print(f"Password for {args.username}: {password}")
        else:
            print(f"Password reset for {args.username}.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
