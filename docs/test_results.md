# Test results and verification notes

The regression scripts below were each run with `DATABASE_URL=sqlite:///./smart_attendance.test_copy.db` after copying the real database to a fresh `smart_attendance.test_copy.db`. No test was run against the real database.

## Validator regression

Fresh-copy run of `backend/scripts/test_validator.py`:

```text
year clash valid: PASS
year clash invalid with pending entry: PASS -> Academic year slot already occupied.
faculty clash valid: PASS
faculty clash invalid with pending entry: PASS -> Faculty is already assigned in this slot.
lab clash valid: PASS
lab clash invalid with pending entry: PASS -> Laboratory room is already booked in this slot.
daily limit valid: PASS
daily limit invalid: PASS -> Faculty exceeds the daily limit of 3 periods.
weekly limit valid: PASS
weekly limit invalid: PASS -> Faculty exceeds the weekly limit of 15 periods.
faculty availability valid: PASS
faculty availability invalid: PASS -> Faculty is marked unavailable for this slot.
lab room consistency invalid theory-with-lab: PASS -> Theory subjects must not be assigned a laboratory room.
lab room consistency invalid lab-without-room: PASS -> Lab subjects must be assigned a laboratory room.
lab room consistency valid theory-without-lab: PASS
lab room consistency valid lab-with-lab: PASS
validate_single_entry pass case: PASS -> []
validate_single_entry fail case: PASS -> ['Academic year slot already occupied.', 'Faculty is already assigned in this slot.']
lab block valid start P1: PASS
lab block invalid start P2: PASS
lab block valid start P4: PASS
lab concurrency valid: PASS
lab concurrency invalid: PASS -> All lab rooms are occupied in this slot.
validate_lab_block pass case: PASS -> []
validate_lab_block fail case: PASS -> ['P1: Academic year slot already occupied.', 'P1: Faculty is already assigned in this slot.', 'P1: Laboratory room is already booked in this slot.', 'P1: All lab rooms are occupied in this slot.']
year feasibility catches overload: PASS -> ['Academic year total weekly requirement (103) exceeds available slots (30).']
faculty feasibility catches overload: PASS -> ['Faculty (Test Faculty) is assigned 107 total weekly periods, exceeding the maximum of 15.']
lab feasibility result: PASS -> ['Estimated lab-block requirement (21) exceeds available lab capacity (20).']
full feasibility check returns dict: PASS -> {'year_warnings': ['Academic year total weekly requirement (103) exceeds available slots (30).'], 'faculty_warnings': {7: ['Faculty (Test Faculty) is assigned 107 total weekly periods, exceeding the maximum of 15.']}, 'lab_warnings': ['Estimated lab-block requirement (21) exceeds available lab capacity (20).']}
```

## Department isolation

Fresh-copy run of `backend/scripts/test_department_isolation.py`:

```text
test-dept-b-hod login includes DB-derived department_id: PASS - status=200, response=3, jwt=3
test-dept-b-faculty login includes DB-derived department_id: PASS - status=200, response=3, jwt=3
test-dept-b-student login includes DB-derived department_id: PASS - status=200, response=3, jwt=3
HOD-B cannot access first department /academic-years: PASS - list=200, get=404, update=404, delete=404
HOD-B cannot access first department /students: PASS - list=200, get=404, update=404, delete=404
HOD-B cannot access first department /faculty: PASS - list=200, get=404, update=404, delete=404
HOD-B cannot access first department /subjects: PASS - list=200, get=404, update=404, delete=404
HOD-B cannot access first department /labs: PASS - list=200, get=404, update=404, delete=404
First-department HOD cannot access B /academic-years: PASS - list=200, get=404, update=404, delete=404
First-department HOD cannot access B /students: PASS - list=200, get=404, update=404, delete=404
First-department HOD cannot access B /faculty: PASS - list=200, get=404, update=404, delete=404
First-department HOD cannot access B /subjects: PASS - list=200, get=404, update=404, delete=404
First-department HOD cannot access B /labs: PASS - list=200, get=404, update=404, delete=404
Face-registration status is department-scoped: PASS - cross statuses=404/404
Faculty availability is department-scoped: PASS - cross create=404, B create=200, cross delete=404
HOD-B cannot create a subject with first-department faculty: PASS - status=400, body={"detail":"Faculty does not belong to this department."}
Mismatched academic-year department is rejected: PASS - status=403
HOD-B cannot move a subject into a first-department academic year: PASS - status=404
HOD-B timetable generation uses only B labs; first-department count unchanged: PASS - status=200, placed=3, B lab ids=[5], first-department entries=33->33
Timetable year/faculty/department/update/delete are department-scoped: PASS - year=200/404, cross faculty=404, entry update/delete=404/404/cross lab=404/404/404
First-department and B lab use at same slot is allowed; extra B use exceeds B capacity: PASS - First-department slot=MONDAY/P4, B capacity before=True (None), additional B use after=False (All lab rooms are occupied in this slot.)
Attendance sessions stay within the HOD department: PASS - create=200, cross get=404, cross start=404
Attendance reports stay within the HOD department: PASS - B student in B daily report=True, in first-department report=False, cross student/year statuses=404/404
HOD-B dashboard counts exclude first-department data: PASS - status=200, counts={'academic_years': 3, 'students': 1, 'faculty': 1, 'subjects': 1, 'labs': 1, 'students_face_registered': 0, 'students_face_not_registered': 1}
OVERALL: PASS (24/24 checks)
```

## Student and attendance full flow

Fresh-copy run of `backend/scripts/test_full_flow.py`:

```text
a. Faculty session ownership: PASS - owner start=200, other faculty start=403
b. Present marks, duplicate rejection, and wrong-year rejection: PASS - student A=200, student B=200, duplicate=400, wrong year=400
c. Close backfill, closed-session rejection, and reopen after close: PASS - while open second start=400, close=200, absent=6/6, mark after close=400, start after close=200
d. Student summary matches DB and history omits another student's rows: PASS - summary=200, exact DB match=True, history=200, owned rows exact=True, newest-first=True, subject filter=200/2 of 2, other student's rows present in DB=True
e. Student role is forbidden from reports, generation, and sessions: PASS - reports=[403, 403, 403, 403], generate=403, sessions=403
f. Other-department HOD receives 404 for session and report rows: PASS - session=404, report rows=404
g. Student timetable is limited to the student's academic year: PASS - status=200, rows=11/11, year ids=[1]
h. /departments/me for HOD: PASS - status=200, department={'id': 1, 'name': 'MCA'}
h. /departments/me for FACULTY: PASS - status=200, department={'id': 1, 'name': 'MCA'}
h. /departments/me for STUDENT: PASS - status=200, department={'id': 1, 'name': 'MCA'}
h. /departments/me for second-department HOD: PASS - status=200, department={'id': 2, 'name': 'MTech'}
Student self profile: PASS - status=200, body={'name': 'Flow Test Student A', 'roll_number': 'FLOW-A-68a322b600', 'email': 'flow-a-68a322b600@example.invalid', 'academic_year_name': '1st Year', 'department_name': 'MCA', 'face_registered': False}
OVERALL: PASS (12/12 checks)
```

## Backtracking regression

Fresh-copy run of `backend/scripts/test_backtracking.py`:

```text
Year 1st Year (id=1, department_id=1): PASS - required=11, placed=11, rows=11, unscheduled=0, uniqueness_violations=0
Year 2nd Year (id=2, department_id=1): PASS - required=11, placed=11, rows=11, unscheduled=0, uniqueness_violations=0
Year 3rd Year (id=3, department_id=1): PASS - required=11, placed=11, rows=11, unscheduled=0, uniqueness_violations=0
Year 1st Year (id=4, department_id=2): PASS - required=11, placed=11, rows=11, unscheduled=0, uniqueness_violations=0
Year 2nd Year (id=5, department_id=2): PASS - required=11, placed=11, rows=11, unscheduled=0, uniqueness_violations=0
a. All MCA/MTech academic years fully schedule: PASS - MCA years=3, MTech years=2, expected total entries=55
d. Deterministic regeneration: PASS - year_id=1, entries=11, identical=True, nodes/result=11
e. Regeneration is a clean rebuild; other years untouched: PASS - target rows=11, placed_count=11, other_years_unchanged=True
b. Greedy vs backtracking tight case: PASS - greedy placed=6, unscheduled=[{'subject_name': 'Constrained Lab Block', 'reason': 'Could not find a valid 3-consecutive-period slot after trying all days, start periods, and labs.'}]; backtracking placed=9, unscheduled=[]
c. Impossible fully unavailable requirement terminates with shortfall: PASS - required=3, placed=0, unscheduled=3, nodes=30, max_nodes=50000, elapsed_seconds=0.270, reason=Could not find a valid single-period slot after trying all day/period combinations.
OVERALL: PASS (5/5 checks)
```

The MTech seed-generation run reported a passing capacity check and 11 placed entries with no unscheduled blocks for each of its two years:

```text
Capacity check: PASS (faculty <= 15 and academic years <= 30)
1st Year: placed_count=11, unscheduled=[], feasibility_warnings={'year_warnings': [], 'faculty_warnings': {}, 'lab_warnings': []}
2nd Year: placed_count=11, unscheduled=[], feasibility_warnings={'year_warnings': [], 'faculty_warnings': {}, 'lab_warnings': []}
```

The suggested 16-period impossible-case example was not used for the regression: an exploratory run placed 16 entries because the existing faculty daily/weekly checks count already-pending entries before the candidate is added. Those checks and their messages were left unchanged as required; the regression instead verifies an impossible case by marking every faculty slot unavailable.

## Test script safety and archived validator output

`test_department_isolation.py`, `test_full_flow.py`, and `test_backtracking.py` refuse a database filename other than `smart_attendance.test_copy.db`. `test_validator.py` uses `SessionLocal` and writes fixtures; point its `DATABASE_URL` at a disposable test copy before running. `test_face_libs.py` does not use the application DB but can download a detector model.

`backend/test_runner_utils.py` is a pytest-oriented support/test module containing a mocked DB helper and validator unit tests; it is not the timetable generator. `backend/validator_output.txt` is an older captured validator run with a lab-feasibility FAIL expectation. Its output is stale and is superseded/replaced for reporting purposes by the fresh passing validator run above; the file itself was retained.

## UNVERIFIED

- Same-person recognition scores across genuinely different camera angles, lighting, and expressions remain unvalidated, as noted in `backend/testing_notes_phase10.md`.
