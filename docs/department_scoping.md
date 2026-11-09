# Department ownership and access

## Source of ownership

`get_user_department_id(db, user)` in `backend/app/core/security.py` derives ownership from database-backed records:

- HOD: `User.department_id`.
- FACULTY: the linked `Faculty.department_id`, using `User.faculty_id`.
- STUDENT: the linked `Student.department_id`, using `User.student_id`.

Missing profile/department assignment raises 403 with “Account has no department assigned.” Department identity is not accepted from a request parameter or trusted from a JWT department claim. Login includes a derived department id in the JWT and response, but protected requests reload the user and resolve ownership from the database.

`require_dept_match` is a helper that raises 404 if the resolved department differs from a record's department. Several routers instead express the same policy with scoped queries or inline department comparisons.

## 404 and 403 behavior

- An unsupported role is rejected by `require_role` with 403.
- For a supported role, cross-department records are generally hidden as 404, so the response does not disclose that the record exists.
- Faculty-specific ownership restrictions can return 403 when the record is in the caller's department but belongs to another faculty member. For example, faculty cannot edit another faculty member's timetable entry.

## Role access summary

| Role | Scope |
|---|---|
| HOD | Management and reporting for the HOD's own department. Cross-department entity ids are not exposed. |
| FACULTY | Department-scoped read views; own timetable and attendance sessions; reports limited to subjects assigned to that faculty. Management endpoints such as subject/faculty/lab creation remain HOD-only. |
| STUDENT | `/me/*` endpoints resolve the student solely through the authenticated user's `student_id`; profile, timetable, attendance summary, and history do not accept a student id in the URL. |

`GET /departments/me` is available to all three roles and returns the current user's department id and name.

## Labs and timetable generation

Labs have a nullable `department_id`. HOD lab lists and FACULTY lab lists are both filtered by the authenticated user's department. In generation, `run_generation` loads lab ids only from the academic year's department. `check_lab_concurrency` joins existing entries to `Lab` and counts only labs in that department when given `department_id`. Thus independent departments can use their own labs at the same weekday/period without consuming one another's lab capacity.

## Related scope filters

- Academic years, students, faculty, subjects, and labs are listed/queried within department boundaries. Students are scoped through their department and academic year; subjects through `AcademicYear.department_id`.
- Timetable year/faculty/department queries are department-scoped. Faculty edit/delete checks additionally require the entry's faculty id to equal the authenticated faculty id.
- HOD attendance-session listings and reports are department-scoped. Faculty session/report access is further narrowed to their own faculty or assigned subjects.
- HOD dashboard counts, year summaries, attendance, sessions, and warnings are computed for the resolved department.
- Face registration/status is HOD-only and checks that the student belongs to the HOD's department. Recognition candidates are limited to the session's academic year.
