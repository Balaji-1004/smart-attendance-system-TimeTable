import sqlite3

DB = 'smart_attendance.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

print('ALL TABLES:')
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"):
    print(row[0])

print('\n--- face_data')
cur.execute("PRAGMA table_info('face_data')")
for row in cur.fetchall():
    print(row)

print('foreign keys:')
for fk in cur.execute("PRAGMA foreign_key_list('face_data')"):
    print(fk)

print('indexes:')
for idx in cur.execute("PRAGMA index_list('face_data')"):
    print(idx)
    idx_name = idx[1]
    cur.execute(f"PRAGMA index_info('{idx_name}')")
    print('  columns:', cur.fetchall())

conn.close()
