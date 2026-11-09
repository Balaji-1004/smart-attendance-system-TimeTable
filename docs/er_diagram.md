# Entity relationship diagram

The diagram reflects the SQLAlchemy models under `backend/app/models/`. `PK`, `FK`, and `UQ` identify primary keys, foreign keys, and unique columns/constraints. Nullable foreign keys are marked `?`.

```mermaid
erDiagram
    DEPARTMENTS {
        int id PK
        string name UQ
    }
    ACADEMIC_YEARS {
        int id PK
        int department_id FK
        string name
        datetime created_at
        string uq_department_year "UQ department_id + name"
    }
    USERS {
        int id PK
        string username UQ
        string password_hash
        enum role
        int department_id FK "nullable"
        int faculty_id FK "nullable"
        int student_id FK "nullable"
        datetime created_at
    }
    FACULTY {
        int id PK
        int department_id FK "nullable"
        string name
        string faculty_code UQ
        string email UQ
        datetime created_at
    }
    STUDENTS {
        int id PK
        string roll_number UQ
        string name
        string email UQ
        int academic_year_id FK
        int department_id FK
        int user_id FK "nullable"
        boolean face_registered
        datetime created_at
        datetime updated_at
    }
    SUBJECTS {
        int id PK
        int academic_year_id FK
        string name
        string code
        string subject_type
        int weekly_periods
        int faculty_id FK
        datetime created_at
        string uq_year_code "UQ academic_year_id + code"
    }
    LABS {
        int id PK
        int department_id FK "nullable"
        string lab_code UQ
        string name
    }
    FACULTY_AVAILABILITY {
        int id PK
        int faculty_id FK
        enum day
        enum period
        datetime created_at
        string uq_faculty_day_period "UQ faculty_id + day + period"
    }
    TIMETABLE_ENTRIES {
        int id PK
        int academic_year_id FK
        int subject_id FK
        int faculty_id FK
        enum day
        enum period
        int lab_id FK "nullable"
        datetime created_at
        string uq_year_day_period "UQ academic_year_id + day + period"
        string uq_faculty_day_period "UQ faculty_id + day + period"
        string uq_lab_day_period "UQ lab_id + day + period"
    }
    ATTENDANCE_SESSIONS {
        int id PK
        int timetable_entry_id FK
        int faculty_id FK
        int subject_id FK
        int academic_year_id FK
        date date
        datetime start_time
        datetime end_time "nullable"
        enum status
    }
    ATTENDANCE {
        int id PK
        int attendance_session_id FK
        int student_id FK
        int subject_id FK
        int faculty_id FK
        int academic_year_id FK
        date date
        datetime time
        enum status
        int timetable_entry_id FK
        string uq_session_student "UQ attendance_session_id + student_id"
    }
    FACE_DATA {
        int id PK
        int student_id FK_UQ
        blob face_embedding
        datetime created_at
        datetime updated_at
    }

    DEPARTMENTS ||--o{ ACADEMIC_YEARS : owns
    DEPARTMENTS ||--o{ USERS : assigned_to
    DEPARTMENTS ||--o{ FACULTY : contains
    DEPARTMENTS ||--o{ STUDENTS : contains
    DEPARTMENTS o|--o{ LABS : contains
    ACADEMIC_YEARS ||--o{ STUDENTS : enrolls
    ACADEMIC_YEARS ||--o{ SUBJECTS : offers
    ACADEMIC_YEARS ||--o{ TIMETABLE_ENTRIES : schedules
    ACADEMIC_YEARS ||--o{ ATTENDANCE_SESSIONS : groups
    ACADEMIC_YEARS ||--o{ ATTENDANCE : scopes
    FACULTY ||--o{ SUBJECTS : teaches
    FACULTY ||--o{ FACULTY_AVAILABILITY : declares
    FACULTY ||--o{ TIMETABLE_ENTRIES : assigned
    FACULTY ||--o{ ATTENDANCE_SESSIONS : leads
    FACULTY ||--o{ ATTENDANCE : records
    SUBJECTS ||--o{ TIMETABLE_ENTRIES : scheduled_as
    SUBJECTS ||--o{ ATTENDANCE_SESSIONS : tracked_in
    SUBJECTS ||--o{ ATTENDANCE : counted_for
    LABS o|--o{ TIMETABLE_ENTRIES : hosts
    TIMETABLE_ENTRIES ||--o{ ATTENDANCE_SESSIONS : starts
    TIMETABLE_ENTRIES ||--o{ ATTENDANCE : records_for
    ATTENDANCE_SESSIONS ||--o{ ATTENDANCE : contains
    STUDENTS ||--o{ ATTENDANCE : receives
    STUDENTS ||--o| FACE_DATA : has_embedding
    FACULTY o|--o{ USERS : faculty_id
    STUDENTS o|--o{ USERS : student_id
    USERS o|--o{ STUDENTS : user_id
```

The ORM defines `Student.face_data` as one-to-one and `FaceData.student_id` is unique. `User.faculty_id`, `User.student_id`, and `Student.user_id` are nullable foreign keys without database uniqueness constraints; the diagram therefore does not imply a database-enforced one-to-one login link.
