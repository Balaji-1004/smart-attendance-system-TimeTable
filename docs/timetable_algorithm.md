# Timetable algorithm and constraints

## Building blocks and deterministic order

`load_blocks_for_year` in `backend/app/services/timetable_generator.py` loads the year's subjects:

- Each THEORY subject produces one duration-1 block per `weekly_periods`.
- Each LAB subject produces `weekly_periods // 3` duration-3 blocks. A remainder is returned as a loader warning and is not placed as a partial block.
- All LAB blocks precede all THEORY blocks.
- Within each group, blocks are sorted by descending total weekly periods assigned to their faculty for the academic year, then ascending subject id. This makes the most-loaded faculty's blocks go first and makes ties deterministic.

Lab candidates iterate weekdays, start periods `P1` and `P4`, then the department's lab ids. Theory candidates iterate each weekday and period in enum order.

## Search behavior

`run_generation(db, academic_year_id, use_backtracking=True)` uses recursive placement by default. For each block it checks candidate slots in the order above. Each candidate is validated against database entries and the pending assignment. A valid candidate is placed and the search advances to the next block. If a later block cannot be placed, the placement is undone and the next candidate is tried. A LAB block's three entries are placed and undone together.

`MAX_NODES` is 50,000 validator calls. When that limit is reached, search stops and returns the best partial assignment found (the greatest number of consecutive blocks placed in the search order). Remaining blocks are reported as unscheduled with the applicable normal failure reason plus ` (after backtracking search)`. Search is deterministic; it uses no randomization. One INFO log entry per generation reports blocks, validator calls (`nodes`), backtracks, placed entries, and unscheduled count.

Passing `use_backtracking=False` to `run_generation` preserves the old greedy first-fit behavior: it accepts the first valid slot for each block and does not revisit prior choices. Its return shape remains `{"placed": [...], "unscheduled": [...]}`. `generate_timetable` invokes the default backtracking mode.

## Hard constraints and enforcement

| Constraint | Enforcement |
|---|---|
| Only Monday-Friday and periods P1-P6 exist | `WeekDay` and `Period` enums in `backend/app/models/enums.py`; the validator comments that no runtime weekend/lunch slot can be represented. |
| One class per academic-year slot | `check_year_clash`; database unique constraint `uq_year_day_period` on timetable entries. |
| A faculty member cannot teach two entries in one slot | `check_faculty_clash`; database unique constraint `uq_faculty_day_period`. |
| A lab room cannot host two entries in one slot | `check_lab_clash`; database unique constraint `uq_lab_day_period`. |
| Faculty daily and weekly timetable-entry limits are 3 and 15 | `check_faculty_daily_limit` and `check_faculty_weekly_limit`. |
| Faculty unavailable slots cannot be used | `check_faculty_availability` checks `FacultyAvailability`. |
| LAB requires a room; THEORY cannot have a room | `check_lab_room_consistency`. |
| Labs occupy 3 consecutive periods and start only at P1 or P4 | `get_lab_block_periods` returns P1-P3 or P4-P6; `validate_lab_block` rejects other starts. |
| Concurrent occupied lab slots cannot exceed the department's lab count | `check_lab_concurrency`; called by `validate_lab_block` with the year department id during generation. Existing occupied entries are joined to `Lab` and counted only when that lab belongs to the department. |

`check_lab_concurrency` retains its prior unscoped behavior when `department_id` is omitted. For generated schedules, `run_generation` obtains all lab ids whose `Lab.department_id` matches the year and passes that department id into validation.

The faculty daily/weekly checks inspect existing and pending entries before the candidate entry is added. In an exploratory 16-period test, this allowed 16 placements; the validator was not changed in this task, as explicitly required.

## Feasibility warnings

`run_full_feasibility_check` reports (does not itself stop placement for) academic-year requirements over 30 weekly periods, faculty assignments over 15 weekly periods, and an estimated lab capacity. Lab capacity is approximated as 10 lab blocks per lab (two valid starts per weekday); the source explicitly describes this as an estimate rather than a scheduling guarantee. Scheduling can still return unscheduled blocks.

## Regeneration behavior

`generate_timetable` deletes all `TimetableEntry` rows for the selected academic year before generating and inserting replacement entries. It commits inside the service function and rolls back on an exception. Manual edits for that year are therefore discarded when it is regenerated.

## Regression evidence

The fresh-copy backtracking regression passed for all five MCA/MTech academic years: 55 expected entries were placed with none unscheduled. It also verified a tight case where greedy placed 6 of 9 entries and left a lab block unscheduled, while backtracking placed all 9; deterministic repeated generation; and an impossible case where all periods were unavailable to the faculty (0 of 3 placed, 30 validator calls). See [test_results.md](./test_results.md).
