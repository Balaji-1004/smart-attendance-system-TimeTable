# Department ownership and access

## Programme structure

The application structure is one department, `Computer Science`, with MCA and MTech programmes. A `Programme` belongs to one department. An `AcademicYear` references both its department and programme; API creation and update verify that the selected programme belongs to the caller's department. Academic-year names are unique within a programme, so `1st Year` can exist in both MCA and MTech.

## Source of ownership

`get_user_department_id(db, user)` in `backend/app/core/security.py` derives ownership from database-backed records:

- HOD: `User.department_id`.
- FACULTY: the linked `Faculty.department_id`, using `User.faculty_id`.
- STUDENT: the linked `Student.department_id`, using `User.student_id`.

Missing profile/department assignment raises 403 with “Account has no department assigned.” Department identity is not accepted from a request parameter or trusted from a JWT department claim. Login includes a derived department id in the JWT and response, but protected requests reload the user and resolve ownership from the database.

`require_dept_match` raises 404 if the resolved department differs from a record's department. Some routers instead implement the same policy with scoped queries or inline department comparisons.

## 404 and 403 behavior

- An unsupported role is rejected by `require_role` with 403.
- Cross-department resources generally appear as 404 so their existence is not disclosed.
- Faculty-specific ownership restrictions can return 403 when a record belongs to the caller's department but another faculty member. For example, faculty cannot edit another faculty member's timetable entry.

## Role access summary

| Role | Scope |
|---|---|
| HOD | Manages programmes, academic years, students, faculty, subjects, labs, faculty availability, timetables, attendance sessions, and reports for the HOD's department. |
| FACULTY | Department-scoped read views; own timetable and attendance sessions; reports limited to assigned subjects where enforced. Faculty can register or replace their own face embedding. Management endpoints remain HOD-only. |
| STUDENT | `/me/*` endpoints resolve the student through the authenticated user's `student_id`; profile, timetable, attendance summary, and history do not accept a student id in the URL. |

`GET /departments/me` is available to all three roles and returns the current user's department id and name.

## Programmes, years, and labs

`GET /programmes` is available to HOD and FACULTY and returns only the caller's department programmes. Programme create/update/delete is HOD-only; deletion is refused while the programme has academic years. Academic-year list accepts `?programme_id=` and remains department-scoped.

Labs have a nullable `department_id`. HOD and FACULTY lab lists are filtered by the authenticated user's department. During generation, `run_generation` loads lab ids only from the academic year's department. `check_lab_concurrency` joins existing entries to `Lab` and counts only that department's labs when given `department_id`. Thus independent departments can use their own labs at the same weekday/period without consuming one another's lab capacity.

## Related scope filters

- Students are scoped through their department and academic year; subjects through `AcademicYear.department_id`.
- Timetable year/faculty/department queries are department-scoped. Faculty edit/delete checks additionally require the entry's faculty id to match the authenticated faculty id.
- HOD attendance-session listings and reports are department-scoped. Faculty session/report access is further narrowed to their own faculty or assigned subjects.
- HOD dashboard counts, year summaries, attendance, sessions, and warnings are computed for the resolved department; year displays also include the programme name.
- HOD student/faculty face-registration and status routes return 404 for profiles outside the HOD's department; the faculty self-registration route uses `current_user.faculty_id`. Student attendance recognition candidates are limited to the session's academic year. Faculty face recognition is not implemented.

The migrated and seeded test-copy results are documented in [test_results.md](./test_results.md). The current real database could not be migrated because its existing face-embedding hash differs from the migration's required baseline; its data was left unchanged.
