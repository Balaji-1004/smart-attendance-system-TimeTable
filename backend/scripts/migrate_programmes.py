import argparse
import hashlib
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database.database import engine


COUNT_TABLES = (
    "users",
    "faculty",
    "students",
    "face_data",
    "subjects",
    "timetable_entries",
    "attendance_sessions",
    "attendance",
)
LEGACY_FACULTY_NAMES = ("Dr. Ananya Rao", "Prof. Vikram Shah", "Ms. Meera Iyer")


def database_path():
    if engine.url.get_backend_name() != "sqlite":
        raise RuntimeError(f"Expected SQLite, got {engine.url}.")
    path = Path(engine.url.database)
    return path if path.is_absolute() else (BACKEND_DIR / path).resolve()


def connect():
    path = database_path()
    if not path.is_file():
        raise RuntimeError(f"Database does not exist: {path}")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def table_exists(connection, name):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def column_names(connection, table):
    return {row["name"] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def face_embedding_hash(connection):
    digest = hashlib.sha256()
    for row in connection.execute("SELECT face_embedding FROM face_data ORDER BY student_id"):
        digest.update(row["face_embedding"] or b"")
    return digest.hexdigest()


def counts(connection):
    return {
        table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        for table in COUNT_TABLES
    }


def department_reference_counts(connection, department_id):
    references = {}
    for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        table = row["name"]
        if table.startswith("sqlite_"):
            continue
        for foreign_key in connection.execute(f'PRAGMA foreign_key_list("{table}")'):
            if foreign_key["table"] != "departments":
                continue
            column = foreign_key["from"]
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE "{column}"=?',
                (department_id,),
            ).fetchone()[0]
            if count:
                references[f"{table}.{column}"] = count
    return references


def year_counts(connection, year_id):
    return {
        "students": connection.execute(
            "SELECT COUNT(*) FROM students WHERE academic_year_id=?", (year_id,)
        ).fetchone()[0],
        "subjects": connection.execute(
            "SELECT COUNT(*) FROM subjects WHERE academic_year_id=?", (year_id,)
        ).fetchone()[0],
        "timetable_entries": connection.execute(
            "SELECT COUNT(*) FROM timetable_entries WHERE academic_year_id=?", (year_id,)
        ).fetchone()[0],
        "attendance_sessions": connection.execute(
            "SELECT COUNT(*) FROM attendance_sessions WHERE academic_year_id=?", (year_id,)
        ).fetchone()[0],
        "attendance": connection.execute(
            "SELECT COUNT(*) FROM attendance WHERE academic_year_id=?", (year_id,)
        ).fetchone()[0],
    }


def print_plan(connection):
    departments = connection.execute(
        "SELECT id, name FROM departments ORDER BY id"
    ).fetchall()
    print(f"Database: {database_path()}")
    print(f"Before counts: {counts(connection)}")
    print(f"Before face_embedding SHA-256: {face_embedding_hash(connection)}")
    print(
        "Before face_data row count: "
        f"{connection.execute('SELECT COUNT(*) FROM face_data').fetchone()[0]}"
    )
    print(f"Departments: {[dict(row) for row in departments]}")
    for year in connection.execute(
        "SELECT id, department_id, name FROM academic_years ORDER BY id"
    ):
        print(f"Academic year {year['id']} ({year['name']}): {year_counts(connection, year['id'])}")
    print("Planned mapping: years 1-2 -> MCA; years 4-5 -> MTech; year 3 students -> year 2.")
    print(
        "Planned programme department: departments.id=1; department 2 rows and any "
        "department 3 Computer Science rows move to department 1."
    )
    existing_year_ids = {
        row["id"]
        for row in connection.execute("SELECT id FROM academic_years")
    }
    print(
        "Planned MTech years: "
        f"create missing ids from {sorted({4, 5} - existing_year_ids)}."
    )
    print("Planned removal: old teaching records for years 1-3; mtech.hod; unreferenced demo faculty.")


def ensure_programme(connection, department_id, name):
    row = connection.execute(
        "SELECT id FROM programmes WHERE department_id=? AND name=?",
        (department_id, name),
    ).fetchone()
    if row is not None:
        return row["id"]
    cursor = connection.execute(
        "INSERT INTO programmes (department_id, name, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (department_id, name),
    )
    return cursor.lastrowid


def clear_year_teaching_data(connection, year_ids):
    placeholders = ",".join("?" for _ in year_ids)
    if not year_ids:
        return
    query = f"academic_year_id IN ({placeholders})"
    connection.execute(f"DELETE FROM attendance WHERE {query}", year_ids)
    connection.execute(f"DELETE FROM attendance_sessions WHERE {query}", year_ids)
    connection.execute(f"DELETE FROM timetable_entries WHERE {query}", year_ids)
    connection.execute(f"DELETE FROM subjects WHERE {query}", year_ids)


def rebuild_academic_years(connection, programme_ids):
    old_columns = column_names(connection, "academic_years")
    rows = connection.execute(
        "SELECT id, department_id, name, created_at FROM academic_years ORDER BY id"
    ).fetchall()
    year_programmes = {}
    for row in rows:
        if row["id"] == 3:
            continue
        if row["id"] in (1, 2):
            year_programmes[row["id"]] = programme_ids["MCA"]
        elif row["id"] in (4, 5):
            year_programmes[row["id"]] = programme_ids["MTech"]
        elif "programme_id" in old_columns:
            year_programmes[row["id"]] = connection.execute(
                "SELECT programme_id FROM academic_years WHERE id=?", (row["id"],)
            ).fetchone()["programme_id"]
        else:
            raise RuntimeError(
                f"Unexpected academic year id {row['id']}; refusing to guess its programme."
            )

    if "programme_id" in old_columns:
        for year_id, programme_id in year_programmes.items():
            year_name = {
                1: "1st Year",
                2: "2nd Year",
                4: "1st Year",
                5: "2nd Year",
            }.get(year_id)
            if year_name is None:
                year_name = connection.execute(
                    "SELECT name FROM academic_years WHERE id=?", (year_id,)
                ).fetchone()["name"]
            connection.execute(
                "UPDATE academic_years SET department_id=1, programme_id=?, name=? WHERE id=?",
                (
                    programme_id,
                    year_name,
                    year_id,
                ),
            )
        connection.execute("DELETE FROM academic_years WHERE id=3")
        for year_id, year_name in ((4, "1st Year"), (5, "2nd Year")):
            if year_id not in {row["id"] for row in rows}:
                connection.execute(
                    """INSERT INTO academic_years
                       (id, department_id, programme_id, name, created_at)
                       VALUES (?, 1, ?, ?, CURRENT_TIMESTAMP)""",
                    (year_id, programme_ids["MTech"], year_name),
                )
        return

    connection.execute(
        """CREATE TABLE academic_years_new (
            id INTEGER NOT NULL PRIMARY KEY,
            department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
            programme_id INTEGER NOT NULL REFERENCES programmes(id) ON DELETE CASCADE,
            name VARCHAR NOT NULL,
            created_at DATETIME NOT NULL,
            CONSTRAINT uq_programme_year UNIQUE (programme_id, name)
        )"""
    )
    for row in rows:
        if row["id"] == 3:
            continue
        programme_id = year_programmes[row["id"]]
        connection.execute(
            """INSERT INTO academic_years_new
               (id, department_id, programme_id, name, created_at)
               VALUES (?, 1, ?, ?, ?)""",
            (
                row["id"],
                programme_id,
                {
                    1: "1st Year",
                    2: "2nd Year",
                    4: "1st Year",
                    5: "2nd Year",
                }.get(row["id"], row["name"]),
                row["created_at"],
            ),
        )
    existing_year_ids = {row["id"] for row in rows}
    for year_id, year_name in ((4, "1st Year"), (5, "2nd Year")):
        if year_id not in existing_year_ids:
            connection.execute(
                """INSERT INTO academic_years_new
                   (id, department_id, programme_id, name, created_at)
                   VALUES (?, 1, ?, ?, CURRENT_TIMESTAMP)""",
                (year_id, programme_ids["MTech"], year_name),
            )
    connection.execute("DROP TABLE academic_years")
    connection.execute("ALTER TABLE academic_years_new RENAME TO academic_years")
    connection.execute("CREATE INDEX ix_academic_years_id ON academic_years (id)")


def faculty_blockers(connection, faculty_id):
    blockers = {}
    for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        table = row["name"]
        if table.startswith("sqlite_") or table in ("faculty", "users"):
            continue
        for foreign_key in connection.execute(f'PRAGMA foreign_key_list("{table}")'):
            if foreign_key["table"] != "faculty":
                continue
            column = foreign_key["from"]
            total = connection.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE "{column}"=?',
                (faculty_id,),
            ).fetchone()[0]
            if total:
                blockers[f"{table}.{column}"] = total
    return blockers


def migrate(connection):
    before_count = counts(connection)
    before_hash = face_embedding_hash(connection)
    before_face_count = before_count["face_data"]
    before_years = {
        row["id"]: (row["name"], row["created_at"])
        for row in connection.execute(
            "SELECT id, name, created_at FROM academic_years ORDER BY id"
        )
    }
    if not table_exists(connection, "programmes"):
        connection.execute(
            """CREATE TABLE programmes (
                id INTEGER NOT NULL PRIMARY KEY,
                department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
                name VARCHAR NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_department_programme UNIQUE (department_id, name)
            )"""
        )
        connection.execute("CREATE INDEX ix_programmes_id ON programmes (id)")

    department = connection.execute("SELECT id, name FROM departments WHERE id=1").fetchone()
    if department is None:
        raise RuntimeError("Department id 1 is missing.")
    computer_science_department = connection.execute(
        "SELECT id FROM departments WHERE name='Computer Science' AND id<>1 ORDER BY id LIMIT 1"
    ).fetchone()
    source_department_id = None
    if computer_science_department is not None and computer_science_department["id"] == 3:
        source_department_id = 3
        connection.execute(
            "UPDATE departments SET name='Computer Science legacy 3' WHERE id=3"
        )
    duplicate = connection.execute(
        "SELECT id FROM departments WHERE name='Computer Science' AND id<>1"
    ).fetchone()
    if duplicate is not None:
        raise RuntimeError(
            f"Cannot rename department 1: Computer Science already belongs to department {duplicate['id']}."
        )
    connection.execute(
        "UPDATE departments SET name='Computer Science' WHERE id=1"
    )
    programme_ids = {
        name: ensure_programme(connection, 1, name)
        for name in ("MCA", "MTech")
    }

    years = {
        row["id"]: row
        for row in connection.execute(
            "SELECT id, department_id, name FROM academic_years ORDER BY id"
        )
    }
    if not all(year_id in years for year_id in (1, 2)):
        raise RuntimeError("Required MCA academic year ids 1 and 2 must exist.")

    is_legacy_split = (
        department["name"] != "Computer Science"
        or 3 in years
        or connection.execute("SELECT 1 FROM departments WHERE id=2").fetchone() is not None
        or source_department_id is not None
    )
    if is_legacy_split:
        for year_id in (1, 2, 3):
            if year_id in years:
                print(f"Deleting legacy year {year_id} teaching data: {year_counts(connection, year_id)}")
        connection.execute(
            "UPDATE students SET academic_year_id=2, department_id=1 WHERE academic_year_id=3"
        )
        clear_year_teaching_data(connection, [year_id for year_id in (1, 2, 3) if year_id in years])

    if connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='academic_years'"
    ).fetchone() is None:
        raise RuntimeError("academic_years table is missing.")
    rebuild_academic_years(connection, programme_ids)

    if "department_id" in column_names(connection, "faculty"):
        connection.execute("UPDATE faculty SET department_id=1 WHERE department_id=2")
        if source_department_id is not None:
            connection.execute("UPDATE faculty SET department_id=1 WHERE department_id=3")
    if "department_id" in column_names(connection, "labs"):
        connection.execute("UPDATE labs SET department_id=1 WHERE department_id=2")
        if source_department_id is not None:
            connection.execute("UPDATE labs SET department_id=1 WHERE department_id=3")
    if "department_id" in column_names(connection, "users"):
        connection.execute("DELETE FROM users WHERE username='mtech.hod'")
        connection.execute("UPDATE users SET department_id=1 WHERE department_id=2")
        if source_department_id is not None:
            connection.execute("UPDATE users SET department_id=1 WHERE department_id=3")
    connection.execute("UPDATE students SET department_id=1 WHERE department_id=2")
    if source_department_id is not None:
        connection.execute("UPDATE students SET department_id=1 WHERE department_id=3")

    for faculty_name in LEGACY_FACULTY_NAMES:
        faculty = connection.execute(
            "SELECT id FROM faculty WHERE name=?", (faculty_name,)
        ).fetchone()
        if faculty is None:
            continue
        faculty_id = faculty["id"]
        blockers = faculty_blockers(connection, faculty_id)
        if blockers:
            print(f"Keeping demo faculty {faculty_name} (id={faculty_id}); references: {blockers}")
            continue
        connection.execute("DELETE FROM users WHERE faculty_id=?", (faculty_id,))
        connection.execute("DELETE FROM faculty WHERE id=?", (faculty_id,))
        print(f"Deleted unreferenced demo faculty {faculty_name} (id={faculty_id}).")

    if "face_registered" not in column_names(connection, "faculty"):
        connection.execute(
            "ALTER TABLE faculty ADD COLUMN face_registered BOOLEAN NOT NULL DEFAULT 0"
        )
    if not table_exists(connection, "faculty_face_data"):
        connection.execute(
            """CREATE TABLE faculty_face_data (
                id INTEGER NOT NULL PRIMARY KEY,
                faculty_id INTEGER NOT NULL UNIQUE REFERENCES faculty(id),
                face_embedding BLOB NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        connection.execute("CREATE INDEX ix_faculty_face_data_id ON faculty_face_data (id)")

    for department_id in (2, source_department_id):
        if department_id is None:
            continue
        if connection.execute(
            "SELECT 1 FROM departments WHERE id=?", (department_id,)
        ).fetchone() is not None:
            references = department_reference_counts(connection, department_id)
            if references:
                raise RuntimeError(
                    f"Department {department_id} still has references and cannot be deleted: {references}"
                )
            connection.execute("DELETE FROM departments WHERE id=?", (department_id,))

    remaining_year3_students = connection.execute(
        "SELECT COUNT(*) FROM students WHERE academic_year_id=3"
    ).fetchone()[0]
    if remaining_year3_students:
        raise RuntimeError(f"{remaining_year3_students} students still reference academic year 3.")
    if connection.execute("SELECT 1 FROM academic_years WHERE id=3").fetchone() is not None:
        connection.execute("DELETE FROM academic_years WHERE id=3")

    foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise RuntimeError(f"Foreign key check failed: {[tuple(row) for row in foreign_key_errors]}")
    after_years = {
        row["id"]: (row["name"], row["created_at"])
        for row in connection.execute(
            "SELECT id, name, created_at FROM academic_years ORDER BY id"
        )
    }
    expected_retained_years = {
        year_id: value for year_id, value in before_years.items() if year_id != 3
    }
    if any(after_years.get(year_id) != value for year_id, value in expected_retained_years.items()):
        raise RuntimeError(
            f"Academic year ids, names, or created_at values changed unexpectedly: {after_years}"
        )
    required_years = {
        1: ("1st Year", programme_ids["MCA"]),
        2: ("2nd Year", programme_ids["MCA"]),
        4: ("1st Year", programme_ids["MTech"]),
        5: ("2nd Year", programme_ids["MTech"]),
    }
    actual_required_years = {
        row["id"]: (row["name"], row["programme_id"])
        for row in connection.execute(
            "SELECT id, name, programme_id FROM academic_years WHERE id IN (1, 2, 4, 5)"
        )
    }
    if actual_required_years != required_years:
        raise RuntimeError(
            f"Expected academic years 1, 2, 4 and 5 in their programmes; got {actual_required_years}."
        )
    print(
        f"Academic year verification: retained existing ids/names/timestamps except removed year 3; "
        f"before={len(before_years)}, after={len(after_years)}, ids={sorted(after_years)}"
    )
    after_count = counts(connection)
    after_hash = face_embedding_hash(connection)
    print(f"After counts: {after_count}")
    print(f"After face_embedding SHA-256: {after_hash}")
    print(f"After face_data row count: {after_count['face_data']}")
    if after_hash != before_hash:
        raise RuntimeError("Face embedding hash changed during programme migration.")
    if before_face_count != after_count["face_data"]:
        raise RuntimeError("face_data row count changed during programme migration.")


def main():
    parser = argparse.ArgumentParser(description="Migrate department academic years to programmes.")
    parser.add_argument("--apply", action="store_true", help="Apply the migration; otherwise print a dry run.")
    args = parser.parse_args()
    connection = connect()
    try:
        print_plan(connection)
        if not args.apply:
            print("DRY RUN: no changes made.")
            return 0
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        try:
            migrate(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.execute("PRAGMA foreign_keys=ON")
        print("APPLY: committed successfully.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
