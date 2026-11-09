import hashlib
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database.database import engine


ROW_COUNT_QUERIES = {
    "users": "SELECT COUNT(*) FROM users",
    "faculty": "SELECT COUNT(*) FROM faculty",
    "students": "SELECT COUNT(*) FROM students",
    "face_data": "SELECT COUNT(*) FROM face_data",
    "subjects": "SELECT COUNT(*) FROM subjects",
    "timetable_entries": "SELECT COUNT(*) FROM timetable_entries",
    "attendance_sessions": "SELECT COUNT(*) FROM attendance_sessions",
    "attendance": "SELECT COUNT(*) FROM attendance",
}


def get_database_path():
    if engine.url.get_backend_name() != "sqlite":
        raise RuntimeError(f"Expected a SQLite database, got {engine.url}.")
    if not engine.url.database:
        raise RuntimeError("The configured SQLite database URL has no file path.")
    return Path(engine.url.database).resolve()


def get_row_counts(connection):
    return {
        table: connection.execute(query).fetchone()[0]
        for table, query in ROW_COUNT_QUERIES.items()
    }


def get_face_embeddings_hash(connection):
    digest = hashlib.sha256()
    rows = connection.execute(
        "SELECT face_embedding FROM face_data ORDER BY student_id"
    )
    for (embedding,) in rows:
        if embedding is None:
            digest.update(b"\x00")
        else:
            digest.update(embedding)
    return digest.hexdigest()


def ensure_department_column(connection, table):
    columns = {
        row[1] for row in connection.execute(f"PRAGMA table_info('{table}')")
    }
    if "department_id" in columns:
        print(f"{table}.department_id already exists; skipping")
        return
    print(f"Adding {table}.department_id")
    connection.execute(f"ALTER TABLE {table} ADD COLUMN department_id INTEGER")


def print_counts(title, counts):
    print(title)
    for table, count in counts.items():
        print(f"  {table}: {count}")


def main():
    database_path = get_database_path()
    print(f"Database: {database_path}")
    if not database_path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {database_path}")

    connection = sqlite3.connect(database_path, isolation_level=None)
    try:
        connection.execute("BEGIN IMMEDIATE")
        before_counts = get_row_counts(connection)
        before_hash = get_face_embeddings_hash(connection)
        print_counts("Row counts before migration:", before_counts)
        print(f"Face embedding SHA-256 before: {before_hash}")

        department = connection.execute(
            "SELECT id FROM departments WHERE name = ?",
            ("Computer Science",),
        ).fetchone()
        if department is None:
            raise RuntimeError(
                "Required department 'Computer Science' does not exist; "
                "migration stopped without creating it."
            )
        department_id = department[0]

        ensure_department_column(connection, "users")
        ensure_department_column(connection, "faculty")

        faculty_updated = connection.execute(
            """
            UPDATE faculty
            SET department_id = ?
            WHERE department_id IS NOT ?
            """,
            (department_id, department_id),
        ).rowcount
        hods_updated = connection.execute(
            """
            UPDATE users
            SET department_id = ?
            WHERE role = 'HOD' AND department_id IS NOT ?
            """,
            (department_id, department_id),
        ).rowcount
        print(f"Faculty rows backfilled: {faculty_updated}")
        print(f"HOD user rows backfilled: {hods_updated}")

        after_counts = get_row_counts(connection)
        after_hash = get_face_embeddings_hash(connection)
        print_counts("Row counts after migration:", after_counts)
        print(f"Face embedding SHA-256 after:  {after_hash}")
        if before_hash != after_hash:
            raise RuntimeError("Face embedding hash changed during migration.")
        print("Face embedding hashes match.")

        connection.commit()
        print("Migration committed.")
    except Exception:
        connection.rollback()
        print("Migration failed; transaction rolled back.", file=sys.stderr)
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
