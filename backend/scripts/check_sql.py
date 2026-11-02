import sqlite3

conn = sqlite3.connect('smart_attendance.db')
cur = conn.cursor()
for name in ['attendance', 'attendance_sessions']:
    print('---', name)
    print(cur.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone())
conn.close()
