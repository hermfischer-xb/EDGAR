"""Cases for the required context ordering, the filing-date bound and business-day arithmetic.

Extracts selectRequiredContext and its helpers by AST from validate/RequiredContext.py, or from
validate/Filing.py on commits before the move, so it runs without Arelle.
Usage: python3 test_select_required_context.py [path to EDGAR plugin checkout]   (or set EDGAR_PLUGIN)
"""
import ast, datetime, os, sys

PLUGIN = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("EDGAR_PLUGIN", ".")
# the selector lives in RequiredContext.py since its move out of Filing.py; older commits still have it in Filing.py
F = os.path.join(PLUGIN, "validate", "RequiredContext.py")
if not os.path.exists(F):
    F = os.path.join(PLUGIN, "validate", "Filing.py")
print("reading", F)
# the step 4 submission sets, reduced to the types these cases use
ns = {"datetime": datetime, "exgRequiredContextDurationSubmissionTypes": frozenset({"10-K", "10-Q", "8-K", "DEF 14A"})}
wanted = ("usFederalHolidaysObserved", "businessDayOffset", "contextLastDay", "selectRequiredContext")
src = ast.parse(open(F, encoding="utf-8").read())
for n in src.body:  # module constants the functions close over, then the functions
    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "EDGAR_OBSERVED_CLOSURES":
        exec(compile(ast.Module([n], []), F, "exec"), ns)
for n in src.body:
    if isinstance(n, ast.FunctionDef) and n.name in wanted:
        exec(compile(ast.Module([n], []), F, "exec"), ns)
sel, businessDayOffset = ns["selectRequiredContext"], ns["businessDayOffset"]
# Since hf-exg-required-context-data the caller decides whether step 4 applies (from the submission's EXG
# submission sets) and passes durationWindow; these cases name a submission type, so translate it here
if sel.__code__.co_varnames[1] == "durationWindow":
    _select, _step4 = sel, ns["exgRequiredContextDurationSubmissionTypes"]
    sel = lambda contexts, submissionType, *a, **k: _select(contexts, submissionType.partition("\u00a7")[0] in _step4, *a, **k)

D = datetime.datetime
class C:
    """A context with only the attributes the selector reads."""
    def __init__(s, id, start, end, dims=(), instant=False):
        s.id = id; s.startDatetime = None if instant else D(*start); s.endDatetime = D(*end)
        s.isStartEndPeriod = not instant; s.isInstantPeriod = instant
        s.qnameDims = dict.fromkeys(dims); s.dimsHash = hash(tuple(dims))
    def isEntityIdentifierEqualTo(s, o): return True
    def __repr__(s): return s.id

fy   = C("FY",   (2024,7,1),  (2025,7,1))    # 365 days, 4 quarters
fy2  = C("FY2",  (2024,7,2),  (2025,7,1))    # 364 days, 4 quarters, same end as FY
q4   = C("Q4",   (2025,4,1),  (2025,7,1))    # 91 days, 1 quarter
day  = C("D",    (2025,6,30), (2025,7,1))    # 24 hours
inst = C("I",    None,        (2025,7,1), instant=True)
p24  = C("P24",  (2024,5,27), (2025,5,25))   # 363 days, 4 quarters, earlier end
p25  = C("P25",  (2025,5,26), (2026,5,31))   # 370 days, 4 quarters, later end
y25  = C("Y25",  (2025,1,1),  (2026,1,1))    # calendar 2025, date-only end held as the next midnight
y26  = C("Y26",  (2026,1,1),  (2027,1,1))    # calendar 2026, a forward-looking plan year
y35  = C("Y35",  (2035,1,1),  (2036,1,1))    # a mistyped future year
filed = datetime.date(2026, 3, 15)

# (name, eligible contexts, submission type, DocumentPeriodEndDate contexts, expected id, expected step)
cases = [
 ("4b: one DocumentPeriodEndDate context",        [fy, q4, inst], "10-Q",    {q4},      "Q4",  "4b"),
 ("4c: one longest duration",                     [q4, fy, inst], "10-K",    set(),     "FY",  "4c"),
 ("4c: two DocumentPeriodEndDate contexts",       [q4, fy],       "10-K",    {q4, fy},  "FY",  "4c"),
 ("4d: equally long, latest end (proxy)",         [p24, p25],     "DEF 14A", set(),     "P25", "4d"),
 ("4d: document order does not decide it",        [p25, p24],     "DEF 14A", set(),     "P25", "4d"),
 ("4e: equally long and ending together",         [fy, fy2],      "10-K",    set(),     "FY",  "4e"),
 ("5: submission type outside the step 4 sets",   [fy, day],      "S-1",     set(),     "D",   "5"),
 ("7: only a duration over 371 days",             [C("L", (2020,1,1), (2025,1,1))], "10-K", set(), "L", "7"),
 ("none: no eligible duration",                   [inst],         "10-K",    set(),     None,  None),
]
# the filing-date bound, applied before step 3: (name, eligible, type, filing date, expected id, step)
boundCases = [
 ("bound: future plan year never enters",         [y25, y26],     "DEF 14A", filed, "Y25", "4c"),
 ("bound: mistyped 2035 year never enters",       [y35, y25],     "DEF 14A", filed, "Y25", "4c"),
 ("bound: absent without a filing date",          [y25, y26],     "DEF 14A", None,  "Y26", "4d"),
 ("bound: every context later, so keep them all", [y26, y35],     "DEF 14A", filed, "Y35", "4d"),
 ("bound: one business day after filing is kept", [C("W", (2026,3,16), (2026,3,17))], "8-K", filed, "W", "5"),
]
# businessDayOffset: (name, from, offset, expected)
dayCases = [
 ("+1 over a Friday holiday (4 July 2026 observed Fri 3)", datetime.date(2026,7,2),  1, datetime.date(2026,7,6)),
 ("-5 business days over a weekend",                       datetime.date(2026,3,16), -5, datetime.date(2026,3,9)),
 ("+1 from a Friday",                                      datetime.date(2026,3,13), 1, datetime.date(2026,3,16)),
 ("-5 over Thanksgiving 2026 (Thu 26 Nov)",                datetime.date(2026,11,30), -5, datetime.date(2026,11,20)),
 ("+1 over New Year (1 Jan 2027 is a Friday)",             datetime.date(2026,12,31), 1, datetime.date(2027,1,4)),
 ("-5 over the 2025-01-09 day of mourning",                datetime.date(2025,1,13), -5, datetime.date(2025,1,3)),
 ("-5 over the observed 24/26 Dec 2025 closures",          datetime.date(2025,12,29), -5, datetime.date(2025,12,17)),
]

# step 4b skipped where the submission type makes dei:DocumentPeriodEndDate optional (hf-exg-required-context-4b);
# selectors without that argument (before it) are tested only on the cases above
import inspect
optionalCases = [
 ("4b skipped when the fact is optional",         [fy, q4, inst], "DEF 14A", {q4},      "FY",  "4c"),
 ("4b kept when the fact is required",            [fy, q4, inst], "DEF 14A", {q4},      "Q4",  "4b"),
]
takesRequired = "documentPeriodEndDateRequired" in inspect.signature(sel).parameters
ok = True
if takesRequired:
    for (name, elig, submissionType, dped, wantId, wantStep), req in zip(optionalCases, (False, True)):
        c, step = sel(elig, submissionType, dped, None, req)
        got = (getattr(c, "id", None), step); good = got == (wantId, wantStep); ok &= good
        print("PASS" if good else "FAIL", f"{name:52}", got)
for name, elig, submissionType, dped, wantId, wantStep in cases:
    c, step = sel(elig, submissionType, dped)
    got = (getattr(c, "id", None), step); good = got == (wantId, wantStep); ok &= good
    print("PASS" if good else "FAIL", f"{name:52}", got)
for name, elig, submissionType, filingDate, wantId, wantStep in boundCases:
    c, step = sel(elig, submissionType, set(), filingDate)
    got = (getattr(c, "id", None), step); good = got == (wantId, wantStep); ok &= good
    print("PASS" if good else "FAIL", f"{name:52}", got)
for name, start, offset, want in dayCases:
    got = businessDayOffset(start, offset); good = got == want; ok &= good
    print("PASS" if good else "FAIL", f"{name:52}", got.isoformat())
print("ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
