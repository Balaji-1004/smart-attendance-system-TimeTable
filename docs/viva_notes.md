# Viva preparation: likely questions

1. **What problem does the project address and what technologies does it use?**  
   It manages one Computer Science department containing MCA and MTech programmes, including academic data, timetables, attendance sessions, reports, and student self-service. The backend uses FastAPI, SQLAlchemy, and SQLite; the frontend uses React/Vite; authentication uses JWT; face processing uses MediaPipe and DeepFace.

2. **What are the three roles?**  
   HOD, FACULTY, and STUDENT. Backend dependencies enforce role access independently of frontend route restrictions.

3. **How is a request authenticated?**  
   The bearer token is decoded, its `sub` is parsed as a user id, and the user is reloaded from the database.

4. **How is a user's department determined?**  
   `get_user_department_id` reads the HOD's user department or follows the faculty/student profile foreign key to that profile's department.

5. **Why return 404 for cross-department records?**  
   Returning 404 avoids revealing another department's records; 403 is reserved for roles or ownership actions explicitly forbidden. The client-supplied department id does not establish authorization.

6. **How are database tables initialized, and how are programmes related to years?**
   `init_db` invokes SQLAlchemy `Base.metadata.create_all`; it creates missing tables but does not upgrade existing tables. The repository has targeted SQLite migrations, not Alembic. A programme belongs to a department, and each academic year belongs to both; `1st Year` can exist in both MCA and MTech.

7. **How are lab blocks represented?**  
   Each complete set of three weekly lab periods creates a three-period block. Any remainder is reported and left unscheduled.

8. **How does timetable generation order blocks?**  
   `run_generation` places labs before theory. Within each group, blocks are sorted by descending total weekly periods assigned to the faculty, then by subject id.

9. **Does the generator backtrack?**  
   Yes, by default it recursively tries candidates in deterministic order, validates against the pending schedule, and undoes a block when a later placement fails. `use_backtracking=False` preserves greedy first-fit behavior.

10. **How is the search bounded?**  
    It stops after `MAX_NODES = 50000` validator calls and returns the best partial assignment found, marking remaining blocks with an after-backtracking-search reason suffix.

11. **When may a lab block start?**  
    Only at P1 (P1-P3) or P4 (P4-P6), enforced by `get_lab_block_periods` and `validate_lab_block`.

12. **How does the system avoid timetable clashes?**  
    Validator checks reject occupied year, faculty, and lab slots; database unique constraints also protect year/day/period, faculty/day/period, and lab/day/period.

13. **What faculty load limits are checked?**  
    The validator limits a faculty member to 3 scheduled periods per day and 15 per week, counting the candidate. Existing and pending rows are deduplicated by entry id, and moved entries are excluded from both sources.

14. **How is lab capacity separated across departments?**  
    Generation supplies the academic year's department id; lab ids and existing occupied slots are filtered to labs owned by that department.

15. **What happens when a timetable is regenerated?**  
    The generator deletes the selected academic year's existing timetable entries and commits new placements, so manual edits for that year are replaced.

16. **How is attendance associated with a class?**  
    An attendance session references a timetable entry, faculty, subject, and academic year. Attendance rows reference the session and student.

17. **How are duplicate attendance marks prevented?**  
    The endpoint checks for an existing student/session row, and `uq_session_student` enforces uniqueness in the database.

18. **How are absences handled?**  
    Closing a session inserts explicit ABSENT rows for every student in that academic year without an existing row for that session.

19. **Does recognition itself save attendance?**  
    No. It returns a recognition result; the operator must separately submit a manual mark request after review.

20. **What does MediaPipe do, and how does faculty face registration work?**
    MediaPipe Tasks checks for exactly one face before embedding extraction. HOD can register a department faculty face, and faculty can register their own. Those embeddings are stored separately and are not used in attendance matching; faculty recognition is not implemented.

21. **What does DeepFace do?**  
    The route calls `DeepFace.represent` on the image to compute an embedding; the code does not explicitly pass a model name.

22. **How are face embeddings compared?**  
    The service computes cosine similarity for each registered candidate and selects the highest score.

23. **What is the match threshold and is it configurable?**  
    `MATCH_THRESHOLD` is hard-coded as 0.58 in `face_service.py`; it is not loaded from environment settings.

24. **What is a key limitation of the recognition tests?**  
    Same-person captures across real changes in pose, lighting, and expression have not been validated, as noted in testing notes.

25. **What is the manual fallback for recognition?**  
    Faculty can use the existing manual attendance workflow; recognition results do not automatically save attendance.
