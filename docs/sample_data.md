# Sample attendance data

The records below are **sample data for demonstration**, not verified real-world
attendance. They were created by `backend/scripts/seed_sample_attendance.py` with
fixed random seed `42`.

The seed created 14 CLOSED sessions from 2026-10-19 through 2026-11-11, spread
over both MCA years and THEORY and LAB subjects. Every closed session has one
attendance row per student enrolled in that year (5 students in 1st Year and 8
in 2nd Year):

| Session | Date | Year | Subject |
| ---: | --- | --- | --- |
| 1 | 2026-10-20 | 1st Year | Computer Networks |
| 2 | 2026-10-26 | 1st Year | Operating Systems |
| 3 | 2026-10-27 | 1st Year | Communication Skills |
| 4 | 2026-11-02 | 1st Year | Computer Networks Lab |
| 5 | 2026-11-05 | 1st Year | Operating Systems Lab |
| 6 | 2026-11-04 | 1st Year | Ethical Hacking |
| 7 | 2026-11-11 | 1st Year | Introduction to AI and Expert Systems |
| 8 | 2026-10-19 | 2nd Year | Management Concepts and Strategies |
| 9 | 2026-10-20 | 2nd Year | Software Engineering |
| 10 | 2026-10-27 | 2nd Year | Internet and Web Technologies |
| 11 | 2026-10-28 | 2nd Year | Software Quality Assurance |
| 12 | 2026-11-02 | 2nd Year | Internet and Web Technologies Lab |
| 13 | 2026-11-09 | 2nd Year | Management Concepts and Strategies |
| 14 | 2026-11-10 | 2nd Year | Software Engineering |

Two non-face-registered students per year (student ids 1 and 2 in 1st Year,
and 7 and 9 in 2nd Year) have 4/7 present records. Other non-face-registered
students have 6/7, and face-registered students 3, 6, and 8 have 7/7.

The seed also created one OPEN session with no attendance rows:

| Session | Date | Year | Subject | Faculty login | Face-registered student |
| ---: | --- | --- | --- | --- | ---: |
| 15 | 2026-11-12 | 1st Year | Operating Systems Lab | `mr.seenivasan.r.p` | 3 |

Session start/end times are placed inside the selected timetable period. The
seed's illustrative period windows are P1 09:00-10:00, P2 10:00-11:00,
P3 11:00-12:00, P4 13:00-14:00, P5 14:00-15:00, and P6 15:00-16:00.

From the `backend` directory, rerun with:

```powershell
$env:DATABASE_URL = "sqlite:///./smart_attendance.db"
python scripts/seed_sample_attendance.py
```

The script is idempotent: it skips an existing `(timetable_entry_id, date)`
session, reuses the eligible OPEN session for 2026-11-12, and does not create
duplicate attendance. A second run created 0 CLOSED sessions, 0 attendance
rows, and reused all 14 CLOSED sessions and the OPEN session.
