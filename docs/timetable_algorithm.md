# Timetable algorithm and constraints

## Building blocks and deterministic order

`load_blocks_for_year` in `backend/app/services/timetable_generator.py` loads the academic year's subjects:

- Each THEORY subject produces one duration-1 block per `weekly_periods`.
- Each LAB subject produces `weekly_periods // 3` duration-3 blocks. A nonzero remainder produces a loader warning and is not placed as a partial block.
- LAB blocks are processed before THEORY blocks.
- Within each group, `_order_blocks_by_faculty_periods` sorts by descending total weekly periods assigned to the faculty in that academic year, then ascending subject id.

Theory candidates follow weekday enum order and period enum order. Lab candidates follow weekday order, start at P1 then P4, and iterate the academic year's department lab ids in ascending order.

## Placement and backtracking

`run_generation(db, academic_year_id, use_backtracking=True)` recursively places one block at a time. Every candidate invokes the existing validator using the database entries and the pending entries placed so far. A passing theory candidate adds one entry. A passing lab candidate adds all three consecutive entries as a unit.

If a later block cannot be placed, recursion removes the prior block's candidate entries and tries its next candidate. The generator tracks the longest placed prefix of blocks and returns that best partial assignment if no complete solution is found.

`MAX_NODES = 50000` counts validator calls. When that ceiling is reached, the search stops, returns the best partial assignment, and reports remaining blocks with the normal failure reason plus ` (after backtracking search)`. Search is deterministic and does not randomize candidate order. Each generation emits one INFO log with block count, validator calls (`nodes`), backtracks, placed entries, and unscheduled count.

`run_generation(..., use_backtracking=False)` uses deterministic greedy first-fit placement: it accepts the first valid slot for each block and never revisits an earlier choice. Both modes retain the return shape `{"placed": [...], "unscheduled": [...]}`. `generate_timetable` uses backtracking by default.

## Hard constraints and enforcement

| Constraint | Enforcement |
|---|---|
| Weekdays are Monday-Friday; periods are P1-P6 | `WeekDay` and `Period` enums in `backend/app/models/enums.py`; no other day or period can be represented. |
| One class per academic-year slot | `check_year_clash`; database unique constraint `uq_year_day_period`. |
| A faculty member cannot teach two entries in one slot | `check_faculty_clash`; database unique constraint `uq_faculty_day_period`. |
| A lab room cannot host two entries in one slot | `check_lab_clash`; database unique constraint `uq_lab_day_period`. |
| A faculty member may be scheduled for at most 3 periods per day and 15 per week | `check_faculty_daily_limit` and `check_faculty_weekly_limit` include the candidate being validated and reject totals above the limits. Counts deduplicate database and pending rows by entry id, and omit moved entry ids from both sources. |
| A LAB block counts as three candidate periods | `validate_lab_block` calls the daily and weekly checks with `candidate_count=3`; single-entry validation uses one. |
| Faculty unavailable slots cannot be used | `check_faculty_availability` checks `FacultyAvailability`. |
| LAB requires a room; THEORY cannot have a room | `check_lab_room_consistency`. |
| Labs occupy three consecutive periods and start only at P1 or P4 | `get_lab_block_periods` returns P1-P3 or P4-P6; `validate_lab_block` rejects other starts. |
| Concurrent occupied lab slots cannot exceed the department's lab count | `check_lab_concurrency` is called with the academic year's `department_id`; existing entries are joined to `Lab` and only that department's labs are counted. The generator also selects lab ids from that department. |

`check_lab_concurrency` retains unscoped behavior when called without a department id. In generation it is always supplied with the academic year's department, so another department's simultaneous lab usage does not consume local capacity.

## Feasibility warnings

`run_full_feasibility_check` reports, but does not itself stop placement for, year requirements above 30 periods per week, faculty subject assignments above 15 periods per week, and estimated lab capacity. The lab estimate is 10 blocks per lab (two valid starts per weekday), not a scheduling guarantee. The scheduler can still return unscheduled blocks.

## Regeneration

`generate_timetable` deletes all timetable entries for the selected academic year before generating and inserting replacement entries. It commits the rebuilt schedule and rolls back on an exception. Entries for other academic years are not deleted.

## Regression results

On fresh migrated test copies, the four current academic years (MCA 1st/2nd Year and MTech 1st/2nd Year) scheduled 21, 15, 11, and 11 entries respectively, with no unscheduled blocks or uniqueness violations. The tight regression placed 6 of 9 entries greedily, leaving the constrained lab block unscheduled; backtracking placed all 9. Repeating the same year produced identical entries. A fully unavailable 3-period requirement terminated with 0 placed, 3 unscheduled, and 30 validator calls. See [test_results.md](./test_results.md).
