import hashlib
import sqlite3
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = BACKEND_DIR / "smart_attendance.db"
EXPECTED_FACE_HASH = (
    "f6e5a7c5c387fb582316c48519c656657deb6a407ce089baccab527e0cbc58a9"
)
EXPECTED_FOREIGN_KEY_VIOLATIONS = {
    ("attendance", 1, "timetable_entries", 0),
    ("attendance", 2, "timetable_entries", 0),
    ("attendance", 3, "timetable_entries", 0),
    ("attendance", 4, "timetable_entries", 0),
    ("attendance", 5, "timetable_entries", 0),
    ("attendance_sessions", 1, "timetable_entries", 3),
}
PROTECTED_TABLES = (
    "students",
    "users",
    "subjects",
    "timetable_entries",
    "face_data",
)


def face_embedding_hash(connection):
    digest = hashlib.sha256()
    rows = connection.execute(
        "SELECT student_id, face_embedding FROM face_data ORDER BY student_id"
    )
    for student_id, embedding in rows:
        if embedding is None:
            raise RuntimeError(f"face_embedding is NULL for student_id={student_id}")
        digest.update(bytes(embedding))
    return digest.hexdigest()


def table_counts(connection, tables):
    return {
        table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        for table in tables
    }


def foreign_key_violations(connection):
    return {
        tuple(row)
        for row in connection.execute("PRAGMA foreign_key_check").fetchall()
    }


def main():
    if DATABASE_PATH.name != "smart_attendance.db":
        raise RuntimeError(f"Refusing unexpected database path: {DATABASE_PATH}")

    connection = sqlite3.connect(DATABASE_PATH, isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")

        before_hash = face_embedding_hash(connection)
        if before_hash != EXPECTED_FACE_HASH:
            raise RuntimeError(
                f"Face hash mismatch; expected {EXPECTED_FACE_HASH}, got {before_hash}"
            )
        before_counts = table_counts(connection, PROTECTED_TABLES)
        violations = foreign_key_violations(connection)

        orphan_sessions = connection.execute(
            """
            SELECT s.id
            FROM attendance_sessions AS s
            LEFT JOIN timetable_entries AS t ON t.id = s.timetable_entry_id
            WHERE t.id IS NULL
            ORDER BY s.id
            """
        ).fetchall()

        deleted_attendance = 0
        deleted_sessions = 0
        if orphan_sessions:
            expected_session_ids = {1}
            actual_session_ids = {row[0] for row in orphan_sessions}
            if actual_session_ids != expected_session_ids:
                raise RuntimeError(
                    f"Unexpected orphan session ids: {sorted(actual_session_ids)}"
                )
            if violations != EXPECTED_FOREIGN_KEY_VIOLATIONS:
                raise RuntimeError(
                    f"Foreign-key violations changed: {sorted(violations)}"
                )

            session_ids = sorted(actual_session_ids)
            placeholders = ",".join("?" for _ in session_ids)
            attendance_rows = connection.execute(
                f"""
                SELECT id, status
                FROM attendance
                WHERE attendance_session_id IN ({placeholders})
                ORDER BY id
                """,
                session_ids,
            ).fetchall()
            if len(attendance_rows) != 5 or any(
                row[1] != "ABSENT" for row in attendance_rows
            ):
                raise RuntimeError(
                    "Expected exactly five ABSENT attendance rows for orphan session 1; "
                    f"found {attendance_rows}"
                )

            attendance_ids = [row[0] for row in attendance_rows]
            attendance_placeholders = ",".join("?" for _ in attendance_ids)
            deleted_attendance = connection.execute(
                f"DELETE FROM attendance WHERE id IN ({attendance_placeholders})",
                attendance_ids,
            ).rowcount
            if deleted_attendance != 5:
                raise RuntimeError(
                    f"Expected to delete 5 attendance rows, deleted {deleted_attendance}"
                )

            deleted_sessions = connection.execute(
                "DELETE FROM attendance_sessions WHERE id IN (1)"
            ).rowcount
            if deleted_sessions != 1:
                raise RuntimeError(
                    f"Expected to delete 1 orphan session, deleted {deleted_sessions}"
                )
        elif violations:
            raise RuntimeError(
                f"No orphan session found but foreign-key violations remain: "
                f"{sorted(violations)}"
            )

        after_violations = foreign_key_violations(connection)
        after_hash = face_embedding_hash(connection)
        after_counts = table_counts(connection, PROTECTED_TABLES)
        if after_violations:
            raise RuntimeError(
                f"Foreign-key violations remain after repair: {sorted(after_violations)}"
            )
        if after_hash != before_hash:
            raise RuntimeError(
                f"Face hash changed: before {before_hash}, after {after_hash}"
            )
        if after_counts != before_counts:
            raise RuntimeError(
                f"Protected table counts changed: before {before_counts}, "
                f"after {after_counts}"
            )

        connection.commit()
        print(f"Deleted attendance rows: {deleted_attendance}")
        print(f"Deleted orphan attendance sessions: {deleted_sessions}")
        print(f"Protected table counts unchanged: {after_counts}")
        print(f"Face hash unchanged: {after_hash}")
        print("PRAGMA foreign_key_check: (empty)")
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
