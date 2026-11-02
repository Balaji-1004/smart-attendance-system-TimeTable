import sqlite3

DB = 'smart_attendance.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type=\'table\' ORDER BY name;")
print('tables:', [r[0] for r in cur.fetchall()])

for table in ['departments','academic_years','users','faculty','students']:
    print('\n---', table)
    try:
        cur.execute(f"PRAGMA table_info('{table}')")
        rows = cur.fetchall()
        for r in rows:
            print(r)
    except Exception as e:
        print('error:', e)

conn.close()
