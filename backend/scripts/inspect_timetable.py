import sqlite3

DB = 'smart_attendance.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

table = 'timetable_entries'
print('Table:', table)
print('\nColumns:')
cur.execute(f"PRAGMA table_info('{table}')")
cols = cur.fetchall()
for c in cols:
    print(c)

print('\nForeign keys:')
cur.execute(f"PRAGMA foreign_key_list('{table}')")
for fk in cur.fetchall():
    print(fk)

print('\nIndexes (including UNIQUE constraints):')
cur.execute(f"PRAGMA index_list('{table}')")
indexes = cur.fetchall()
for idx in indexes:
    print(idx)
    idx_name = idx[1]
    cur.execute(f"PRAGMA index_info('{idx_name}')")
    print('  columns:', cur.fetchall())

conn.close()
