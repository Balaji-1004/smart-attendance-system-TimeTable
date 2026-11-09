import argparse
import hashlib
import sqlite3
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = BACKEND_DIR / "smart_attendance.db"

COUNT_QUERIES = {
    "academic_years": "SELECT COUNT(*) FROM academic_years WHERE department_id = ?",
    "students": "SELECT COUNT(*) FROM students WHERE department_id = ?",
    "faculty": "SELECT COUNT(*) FROM faculty WHERE department_id = ?",
    "subjects": """
        SELECT COUNT(*)
        FROM subjects s
        JOIN academic_years ay ON ay.id = s.academic_year_id
        WHERE ay.department_id = ?
    """,
    "labs": "SELECT COUNT(*) FROM labs WHERE department_id = ?",
    "timetable_entries": """
        SELECT COUNT(*)
        FROM timetable_entries te
        JOIN academic_years ay ON ay.id = te.academic_year_id
        WHERE ay.department_id = ?
    """,
    "attendance_sessions": """
        SELECT COUNT(*)
        FROM attendance_sessions sessions
        JOIN academic_years ay ON ay.id = sessions.academic_year_id
        WHERE ay.department_id = ?
    """,
    "attendance": """
        SELECT COUNT(*)
        FROM attendance a
        JOIN academic_years ay ON ay.id = a.academic_year_id
        WHERE ay.department_id = ?
    """,
    "face_data": """
        SELECT COUNT(*)
        FROM face_data fd
        JOIN students s ON s.id = fd.student_id
        WHERE s.department_id = ?
    """,
}


def embedding_hash(connection):
    digest = hashlib.sha256()
    for (embedding,) in connection.execute(
        "SELECT face_embedding FROM face_data ORDER BY student_id"
    ):
        digest.update(embedding or b"")
    return digest.hexdigest()


def department_users(connection, department_id):
    return connection.execute(
        """
        SELECT u.username, u.role
        FROM users u
        LEFT JOIN faculty f ON f.id = u.faculty_id
        LEFT JOIN students s ON s.id = u.student_id
        WHERE CASE
            WHEN u.role = 'HOD' THEN u.department_id
            WHEN u.role = 'FACULTY' THEN COALESCE(f.department_id, u.department_id)
            WHEN u.role = 'STUDENT' THEN COALESCE(s.department_id, u.department_id)
            ELSE u.department_id
        END = ?
        ORDER BY u.username
        """,
        (department_id,),
    ).fetchall()


def print_inventory(connection, heading):
    print(heading)
    for department_id in (1, 2):
        department = connection.execute(
            "SELECT name FROM departments WHERE id = ?", (department_id,)
        ).fetchone()
        if department is None:
            print(f"Department id={department_id}: NOT FOUND")
            continue

        print(f"Department id={department_id}, name={department[0]!r}")
        for table_name, query in COUNT_QUERIES.items():
            count = connection.execute(query, (department_id,)).fetchone()[0]
            if table_name == "face_data":
                print(f"  {table_name} (via students): {count}")
            else:
                print(f"  {table_name}: {count}")

        users = department_users(connection, department_id)
        user_list = ", ".join(f"{username} ({role})" for username, role in users) or "(none)"
        print(f"  users: {len(users)} [{user_list}]")

    print(f"All face_data.face_embedding SHA-256: {embedding_hash(connection)}")


def apply_renames(connection, before_hash):
    connection.execute("BEGIN IMMEDIATE")
    try:
        departments = dict(
            connection.execute("SELECT id, name FROM departments WHERE id IN (1, 2)").fetchall()
        )
        if 1 not in departments or 2 not in departments:
            raise RuntimeError("Both department ids 1 and 2 must exist.")
        if departments[1] != "Computer Science":
            raise RuntimeError(
                f"Department 1 must be 'Computer Science' before apply; found {departments[1]!r}."
            )
        if connection.execute(
            "SELECT 1 FROM departments WHERE name = 'MCA'"
        ).fetchone():
            raise RuntimeError("Cannot rename department 1: a department named 'MCA' already exists.")

        face_count = connection.execute(COUNT_QUERIES["face_data"], (2,)).fetchone()[0]
        attendance_count = connection.execute(COUNT_QUERIES["attendance"], (2,)).fetchone()[0]
        if face_count or attendance_count:
            blockers = []
            if face_count:
                blockers.append(f"{face_count} face_data row(s)")
            if attendance_count:
                blockers.append(f"{attendance_count} attendance row(s)")
            raise RuntimeError(
                "Cannot rename department 2 to 'MTech': blocked by " + " and ".join(blockers) + "."
            )
        if connection.execute(
            "SELECT 1 FROM departments WHERE name = 'MTech'"
        ).fetchone():
            raise RuntimeError("Cannot rename department 2: a department named 'MTech' already exists.")

        connection.execute("UPDATE departments SET name = 'MCA' WHERE id = 1")
        connection.execute("UPDATE departments SET name = 'MTech' WHERE id = 2")
        after_hash = embedding_hash(connection)
        if after_hash != before_hash:
            raise RuntimeError(
                f"Face embedding hash changed unexpectedly: before={before_hash}, after={after_hash}"
            )
        connection.commit()
        print("Department names updated in one transaction.")
        print(f"All face_data.face_embedding SHA-256 after apply: {after_hash}")
        print_inventory(connection, "Inventory after apply:")
    except Exception:
        connection.rollback()
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Inventory and optionally rename department 1 and department 2."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the department name changes. Without this option, only print a dry run.",
    )
    args = parser.parse_args()

    if not DATABASE_PATH.is_file():
        parser.error(f"Database does not exist: {DATABASE_PATH}")

    if args.apply:
        connection = sqlite3.connect(DATABASE_PATH)
    else:
        connection = sqlite3.connect(f"{DATABASE_PATH.as_uri()}?mode=ro", uri=True)

    try:
        before_hash = embedding_hash(connection)
        print(f"Database: {DATABASE_PATH}")
        print_inventory(connection, "Inventory before changes:")
        if args.apply:
            apply_renames(connection, before_hash)
        else:
            print("DRY RUN ONLY: no database changes made. Use --apply to rename.")
    except (sqlite3.Error, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
