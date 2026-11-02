"""Run with:  pytest -q   (or: python test_timetable.py for the demo print)"""
from timetable_generator import SubjectInfo, generate_timetable
from timetable_validator import DAYS, Entry, TimetableState, validate_timetable

def S(i, y, name, typ, wp, f):
    return SubjectInfo(i, y, name, name[:3].upper() + str(i), typ, wp, f)

def sample():
    subs = [
        S(1,1,"Maths","THEORY",3,1), S(2,1,"C Prog","THEORY",3,2), S(3,1,"Digital","THEORY",3,3),
        S(4,1,"English","THEORY",2,4), S(5,1,"C Lab","LAB",3,2),
        S(6,2,"Java","THEORY",3,5), S(7,2,"DBMS","THEORY",3,6), S(8,2,"OS","THEORY",3,7),
        S(9,2,"AI","THEORY",2,8), S(10,2,"Java Lab","LAB",3,5),
        S(11,3,"Cloud","THEORY",3,9), S(12,3,"ML","THEORY",3,10), S(13,3,"IoT","THEORY",2,3),
        S(14,3,"Web Lab","LAB",3,6),
    ]
    return subs, [1, 2], [(5,"Monday",1), (6,"Tuesday",5)]

def test_generated_timetable_has_no_violations():
    subs, labs, unav = sample()
    r = generate_timetable(subs, labs, unav)
    assert validate_timetable(r.entries, labs, unav) == []
    assert r.shortfall_warnings == []

def test_year_clash():
    st = TimetableState([1]); st.add(Entry(1,1,1,"Monday",2))
    assert "Academic year" in st.check_block(1,2,"Monday",[2])

def test_faculty_clash():
    st = TimetableState([1]); st.add(Entry(1,1,1,"Monday",2))
    assert "Faculty is already" in st.check_block(2,1,"Monday",[2])

def test_lab_clash():
    st = TimetableState([1]); 
    for p in (1,2,3): st.add(Entry(1,1,1,"Monday",p,1))
    assert "Lab 1" in st.check_block(2,2,"Monday",[1,2,3],1,True)

def test_lab_must_be_three_consecutive():
    st = TimetableState([1])
    assert "3 consecutive" in st.check_block(1,1,"Monday",[1,3],1,True)
    assert "3 consecutive" in st.check_block(1,1,"Monday",[1,2],1,True)

def test_lab_cannot_cross_lunch():
    st = TimetableState([1])
    assert "P1 or P4" in st.check_block(1,1,"Monday",[2,3,4],1,True)

def test_faculty_daily_limit():
    st = TimetableState([1])
    for p in (1,2,3): st.add(Entry(1,1,1,"Monday",p))
    assert "3 periods per day" in st.check_block(2,1,"Monday",[4])

def test_faculty_weekly_limit():
    st = TimetableState([1])
    for d in DAYS:
        for p in (1,2,3): st.add(Entry(1,1,1,d,p))
    assert "per week" in st.check_block(2,1,"Monday",[5]) or "per day" in st.check_block(2,1,"Monday",[5])

def test_faculty_unavailable():
    st = TimetableState([1],[(1,"Monday",1)])
    assert "unavailable" in st.check_block(1,1,"Monday",[1])

def test_weekend_and_lunch_rejected():
    st = TimetableState([1])
    assert "Saturday" in st.check_block(1,1,"Saturday",[1])
    assert "lunch" in st.check_block(1,1,"Monday",[7])

def test_theory_must_not_use_lab_and_lab_needs_lab():
    st = TimetableState([1])
    assert "must not use" in st.check_block(1,1,"Monday",[1],1,False)
    assert "must use a laboratory" in st.check_block(1,1,"Monday",[1,2,3],None,True)

def test_multiple_labs_run_in_parallel_but_not_beyond_count():
    subs = [S(i,i,f"Lab{i}","LAB",3,i) for i in (1,2,3)]
    st = TimetableState([1,2])
    for s in subs[:2]:
        lab = st.find_free_lab("Monday",[1,2,3]); 
        for p in (1,2,3): st.add(Entry(s.year_id,s.id,s.faculty_id,"Monday",p,lab))
    assert st.find_free_lab("Monday",[1,2,3]) is None

def test_impossible_requirement_reports_shortfall():
    subs = [S(1,1,"Big","THEORY",3,1), S(2,2,"Big2","THEORY",3,1)]   # same faculty
    unav = [(1,d,p) for d in DAYS for p in range(1,7) if not (d=="Monday" and p<=2)]
    r = generate_timetable(subs, [1], unav)
    assert r.shortfall_warnings and "could be scheduled" in r.shortfall_warnings[0]

def test_feasibility_warns_faculty_over_15_and_year_over_30():
    subs = [S(i,1,f"T{i}","THEORY",4,1) for i in range(1,5)]          # 16 periods, one faculty
    r = generate_timetable(subs, [1])
    assert any("maximum is 15" in w for w in r.feasibility_warnings)

def test_regeneration_is_a_clean_rebuild():
    subs, labs, unav = sample()
    a = generate_timetable(subs, labs, unav); b = generate_timetable(subs, labs, unav)
    assert sorted(map(str,a.entries)) == sorted(map(str,b.entries))   # deterministic, old state not reused

def test_manual_move_validated():
    subs, labs, unav = sample()
    r = generate_timetable(subs, labs, unav)
    st = TimetableState(labs, unav)
    for e in r.entries: st.add(e)
    theory = next(e for e in r.entries if e.lab_id is None)
    clash = next(e for e in r.entries if e.lab_id is None and e.year_id == theory.year_id and e != theory)
    assert st.validate_move([theory], clash.day, clash.period) is not None   # year clash
    assert len(st.entries) == len(r.entries)                                 # state untouched

if __name__ == "__main__":
    subs, labs, unav = sample()
    r = generate_timetable(subs, labs, unav)
    print("attempts:", r.attempts, "| unscheduled:", r.best_unscheduled)
    print("feasibility:", r.feasibility_warnings, "| shortfalls:", r.shortfall_warnings)
    names = {s.id: s.name for s in subs}
    for y in (1,2,3):
        print(f"\n--- Year {y} ---")
        for d in DAYS:
            row = []
            for p in range(1,7):
                e = next((x for x in r.entries if x.year_id==y and x.day==d and x.period==p), None)
                row.append((names[e.subject_id] + (f"@L{e.lab_id}" if e.lab_id else "")).ljust(11) if e else "-".ljust(11))
            print(d[:3], "|", " ".join(row))
