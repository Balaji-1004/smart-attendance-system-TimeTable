import sqlite3

DB = 'smart_attendance.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

print('tables:', [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")])

for table in ['attendance_sessions', 'attendance']:
    print('\n---', table)
    cur.execute(f"PRAGMA table_info('{table}')")
    for row in cur.fetchall():
        print(row)
    print('foreign keys:')
    for fk in cur.execute(f"PRAGMA foreign_key_list('{table}')"):
        print(fk)
    print('indexes:')
    for idx in cur.execute(f"PRAGMA index_list('{table}')"):
        print(idx)
        idx_name = idx[1]
        cur.execute(f"PRAGMA index_info('{idx_name}')")
        print('  columns:', cur.fetchall())

conn.close()
