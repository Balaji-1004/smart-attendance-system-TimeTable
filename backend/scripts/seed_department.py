import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal
from app.models import Department


def seed_department():
    db = SessionLocal()
    try:
        existing = db.query(Department).first()
        if existing:
            print(f"Department already exists: id={existing.id}, name={existing.name}")
            return existing

        name_input = input("Enter department name (press Enter for default 'Computer Science'): ").strip()
        department_name = name_input or "Computer Science"

        department = Department(name=department_name)
        db.add(department)
        db.commit()
        db.refresh(department)
        print(f"Department created: id={department.id}, name={department.name}")
        return department
    finally:
        db.close()


if __name__ == "__main__":
    seed_department()
