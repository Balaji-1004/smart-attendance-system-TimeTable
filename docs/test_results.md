# Test results and verification notes

## Test method and data boundary

Each database-writing regression was run on its own fresh `backend/smart_attendance.test_copy.db`, copied from `smart_attendance.backup_before_final_setup.db`. The copy was migrated with `scripts/migrate_programmes.py --apply`, then populated with the MTech and MCA seed scripts before the applicable test. The requested Phase 13 migration and MCA seed were later run on the real database after a separate backup; no regression test was run there.

The historical matching test-copy baseline used face-embedding SHA-256 `0b051a6c5b0a253c5f5786da5a3fe656ecfb65ab93967ae58fd872d6718a5242`; this is an earlier observed value, not a required constant. Migration and seed scripts now compute the hash ordered by student id and the `face_data` row count at each run's start, then require both values to match at the end. The migration retained academic-year ids 1, 2, 4, and 5, and removed year 3 after moving its students to year 2.

## Real database migration and seed

The backup `backend/smart_attendance.backup_before_programmes_apply.db` was created immediately before the real-DB apply (253,952 bytes; original DB 253,952 bytes). The information-only face comparison found the real DB had three embeddings, the historical comparison DB had two, and the shared student id had a different embedding. No face data was modified. Migration and MCA seed both verified a run-specific hash and row count before and after.

```text
Before counts: {'users': 5, 'faculty': 3, 'students': 13, 'face_data': 3, 'subjects': 12, 'timetable_entries': 33, 'attendance_sessions': 5, 'attendance': 19}
Before face_embedding SHA-256: f6e5a7c5c387fb582316c48519c656657deb6a407ce089baccab527e0cbc58a9
Before face_data row count: 3
After migration counts: {'users': 3, 'faculty': 1, 'students': 13, 'face_data': 3, 'subjects': 0, 'timetable_entries': 0, 'attendance_sessions': 0, 'attendance': 0}
After migration face_embedding SHA-256: f6e5a7c5c387fb582316c48519c656657deb6a407ce089baccab527e0cbc58a9
After migration face_data row count: 3
MCA 1st Year: placed_count=21, unscheduled=[]
MCA 2nd Year: placed_count=15, unscheduled=[]
Final counts: {'users': 9, 'faculty': 7, 'students': 13, 'face_data': 3, 'subjects': 12, 'timetable_entries': 36, 'attendance_sessions': 0, 'attendance': 0}
Final face_embedding SHA-256: f6e5a7c5c387fb582316c48519c656657deb6a407ce089baccab527e0cbc58a9
Final face_data row count: 3
Foreign-key violations: []
```

Final inventory is one Computer Science department with MCA and MTech, and four academic years (two per programme). MCA has 13 students, 12 subjects, and 36 timetable entries; MTech currently has 0 students, subjects, and timetable entries. Existing lab/faculty rows were preserved or reassigned as reported by the migration; Ms. Meera Iyer's faculty record remained because it has a faculty-availability reference. Demo passwords were reset separately and are not recorded in this file.

## Programme seeding and timetable generation

After migration and seeding on a fresh test copy:

```text
Capacity check: PASS (faculty <= 15 and academic years <= 30)
MTech timetable generation:
  1st Year: placed_count=11, unscheduled=[], feasibility_warnings={'year_warnings': [], 'faculty_warnings': {}, 'lab_warnings': []}
  2nd Year: placed_count=11, unscheduled=[], feasibility_warnings={'year_warnings': [], 'faculty_warnings': {}, 'lab_warnings': []}
Capacity check: PASS (faculty <= 15/week, each MCA year <= 30/week)
MCA 1st Year: placed_count=21, unscheduled=[], feasibility_warnings={'year_warnings': [], 'faculty_warnings': {}, 'lab_warnings': []}
MCA 2nd Year: placed_count=15, unscheduled=[], feasibility_warnings={'year_warnings': [], 'faculty_warnings': {}, 'lab_warnings': []}
After face_embedding SHA-256: 0b051a6c5b0a253c5f5786da5a3fe656ecfb65ab93967ae58fd872d6718a5242
```

The new faculty/student credentials printed by the seeding scripts were generated for test copies only and are intentionally not recorded here.

Final migrated-and-seeded test-copy inventory:

```text
Departments: [(1, 'Computer Science')]
Programmes: [(1, 1, 'MCA'), (2, 1, 'MTech')]
Academic years: [(1, '1st Year', 1, 'MCA'), (2, '2nd Year', 1, 'MCA'), (4, '1st Year', 1, 'MTech'), (5, '2nd Year', 1, 'MTech')]
Per-programme counts:
('MCA', 14, 12, 36)
('MTech', 8, 8, 22)
Faculty: [('FAC-CS-01', 'Dr T Chithralekha', 1), ('FAC-CS-02', 'Dr Rajpriya Darshini', 1), ('FAC-CS-03', 'Dr G Krishnapriya', 1), ('FAC-CS-04', 'Mr Seenivasan R P', 1), ('FAC-CS-05', 'Dr Sukhvinder Singh', 1), ('FAC-CS-06', 'Dr SL Jayalakshmi', 1), ('FAC-MT-01', 'Dr. Kavya Nair', 1), ('FAC-MT-02', 'Prof. Rajesh Menon', 1), ('FAC-MT-03', 'Ms. Divya Krishnan', 1)]
Labs: [('LAB-001', 'Computer Lab 1', 1), ('LAB-002', 'Computer Lab 2', 1), ('LAB-MT-01', 'MTech Lab 1', 1), ('LAB-MT-02', 'MTech Lab 2', 1)]
Face hash: 0b051a6c5b0a253c5f5786da5a3fe656ecfb65ab93967ae58fd872d6718a5242
```

The counts tuple is `(programme, students, subjects, timetable_entries)`.

## Validator regression

`scripts/test_validator.py` checks existing validator/feasibility cases plus the daily/weekly candidate limits, edit exclusions, and three-period lab candidates. Its latest fresh-copy run ended:

```text
faculty 3rd period allowed: PASS -> 2 existing + candidate = 3
faculty 15th weekly period allowed: PASS -> 14 existing + candidate = 15
faculty 4th period rejected: PASS -> 3 existing + candidate = 4
faculty 16th weekly period rejected: PASS -> 15 existing + candidate = 16
moving entry within same day avoids double counting: PASS -> excluded id=73; reasons=[]
unchanged edit passes limits: PASS -> excluded id=73; reasons=[]
lab block counts three candidate periods: PASS -> daily=3, weekly=3; reasons=[]
OVERALL: PASS (0 failed checks)
```

## Backtracking regression

`scripts/test_backtracking.py` checks all programme years, uniqueness, a greedy trap, an impossible requirement, determinism, and clean regeneration:

```text
Year MCA 1st Year (id=1, department_id=1): PASS - required=21, placed=21, rows=21, unscheduled=0, uniqueness_violations=0
Year MCA 2nd Year (id=2, department_id=1): PASS - required=15, placed=15, rows=15, unscheduled=0, uniqueness_violations=0
Year MTech 1st Year (id=4, department_id=1): PASS - required=11, placed=11, rows=11, unscheduled=0, uniqueness_violations=0
Year MTech 2nd Year (id=5, department_id=1): PASS - required=11, placed=11, rows=11, unscheduled=0, uniqueness_violations=0
a. All MCA/MTech academic years fully schedule: PASS - MCA years=2, MTech years=2, expected total entries=58
d. Deterministic regeneration: PASS - year_id=1, entries=21, identical=True, nodes/result=21
e. Regeneration is a clean rebuild; other years untouched: PASS - target rows=21, placed_count=21, other_years_unchanged=True
b. Greedy vs backtracking tight case: PASS - greedy placed=6, unscheduled=[{'subject_name': 'Constrained Lab Block', 'reason': 'Could not find a valid 3-consecutive-period slot after trying all days, start periods, and labs.'}]; backtracking placed=9, unscheduled=[]
c. Impossible fully unavailable requirement terminates with shortfall: PASS - required=3, placed=0, unscheduled=3, nodes=30, max_nodes=50000, elapsed_seconds=0.470, reason=Could not find a valid single-period slot after trying all day/period combinations.
OVERALL: PASS (5/5 checks)
```

The implemented structure has four academic years total (two per programme); the test checks all four.

## Department isolation

`scripts/test_department_isolation.py` checks login ownership, cross-department 404 behavior, department-scoped programme/year and entity routes, department-local lab capacity, timetable generation, attendance, reports, and dashboard counts. Its latest fresh-copy result:

```text
OVERALL: PASS (24/24 checks)
```

The lab-capacity case confirmed that a simultaneous lab slot in a different department does not consume the test department's capacity, while a second use of its only lab room is rejected.

## Attendance and student portal full flow

`scripts/test_full_flow.py` checks faculty session ownership, present marks and duplicates, close/backfill behavior, student history and summaries, student role restrictions, cross-department 404s, the student timetable, and `/departments/me`:

```text
OVERALL: PASS (12/12 checks)
```

## Programmes and faculty face registration

`scripts/test_programmes.py` checks programme CRUD/scoping, programme-aware academic years (including repeated names across programmes), deletion constraints, faculty face route authorization, zero/multiple-face rejection, re-registration without duplication, and unchanged student `face_data`:

```text
OVERALL: PASS (17/17 checks)
```

## Generator helper checks

`scripts/test_generator_loader.py` passed its block-count and remainder-warning checks. `scripts/test_generator_run.py` generated 11 entries twice for its fixture year, left the other year unchanged, and confirmed consistent counts with no duplicates.
