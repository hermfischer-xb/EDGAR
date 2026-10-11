"""Cases for selectFeeExhibitRequiredContext: a fee exhibit's required context by its anchor facts.

Extracts the functions by AST from validate/RequiredContext.py, so it runs without Arelle.
Usage: python3 test_fee_exhibit_anchor.py [path to EDGAR plugin checkout]   (or set EDGAR_PLUGIN)
"""
import ast, datetime, os, sys

PLUGIN = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("EDGAR_PLUGIN", ".")
F = os.path.join(PLUGIN, "validate", "RequiredContext.py")
ns = {"datetime": datetime, "exgRequiredContextDurationSubmissionTypes": frozenset({"10-K", "10-Q", "8-K"})}
wanted = ("usFederalHolidaysObserved", "businessDayOffset", "contextLastDay", "selectRequiredContext",
          "selectFeeExhibitRequiredContext")
src = ast.parse(open(F, encoding="utf-8").read())
for n in src.body:  # module constants first, then the functions
    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") in ("EDGAR_OBSERVED_CLOSURES", "FEE_EXHIBIT_ANCHORS"):
        exec(compile(ast.Module([n], []), F, "exec"), ns)
for n in src.body:
    if isinstance(n, ast.FunctionDef) and n.name in wanted:
        exec(compile(ast.Module([n], []), F, "exec"), ns)
select, ANCHORS = ns["selectFeeExhibitRequiredContext"], ns["FEE_EXHIBIT_ANCHORS"]
if select.__code__.co_varnames[2] == "durationWindow":  # since hf-exg-required-context-data (see the selector test)
    _select, _step4 = select, ns["exgRequiredContextDurationSubmissionTypes"]
    select = lambda e, a, submissionType, *r, **k: _select(e, a, submissionType in _step4, *r, **k)
assert ANCHORS == ("FeeExhibitTp", "EntityCentralIndexKey", "EntityRegistrantName"), ANCHORS

D = datetime.datetime
class C:
    """A context with only the attributes the selectors read."""
    def __init__(s, id, start, end, instant=False):
        s.id = id; s.startDatetime = None if instant else D(*start); s.endDatetime = D(*end)
        s.isStartEndPeriod = not instant; s.isInstantPeriod = instant
        s.qnameDims = {}
    def __repr__(s): return s.id

day1 = C("DAY1", (2026,3,13), (2026,3,14))   # one day ending on the filing date
day2 = C("DAY2", (2026,3,12), (2026,3,13))   # one day, the day before
yr   = C("YR",   (2025,1,1),  (2026,1,1))    # a calendar year
inst = C("I",    None,        (2026,3,14), instant=True)
other = C("NE",  (2026,3,13), (2026,3,14))   # not eligible (fails steps 1 or 2)
filed = datetime.date(2026, 3, 13)

def anchors(fee=(), cik=(), name=()):
    return [("FeeExhibitTp", set(fee)), ("EntityCentralIndexKey", set(cik)), ("EntityRegistrantName", set(name))]

# (name, eligible, anchor contexts, expected id, expected step)
cases = [
 ("FeeExhibitTp decides over the ordering",          [day1, day2, yr], anchors(fee=[day2], cik=[day1]), "DAY2", "FE:FeeExhibitTp"),
 ("no FeeExhibitTp: the CIK decides",                [day1, day2, yr], anchors(cik=[day2]),             "DAY2", "FE:EntityCentralIndexKey"),
 ("FeeExhibitTp only on an instant: the CIK decides",[day1, day2, inst], anchors(fee=[inst], cik=[day2]), "DAY2", "FE:EntityCentralIndexKey"),
 ("FeeExhibitTp only in an ineligible context",      [day1, day2], anchors(fee=[other], name=[day2]),   "DAY2", "FE:EntityRegistrantName"),
 ("FeeExhibitTp in two durations: ordering among them", [yr, day2, day1], anchors(fee=[day2, day1]),    "DAY1", "FE:FeeExhibitTp/5"),
 ("no anchor fact at all: the ordering as before",   [day2, day1, yr], anchors(),                        "DAY1", "5"),
]
ok = True
for name, elig, anch, wantId, wantStep in cases:
    c, step = select(elig, anch, "424B2", set(), filed)
    got = (getattr(c, "id", None), step); good = got == (wantId, wantStep); ok &= good
    print("PASS" if good else "FAIL", f"{name:52}", got)
print("ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
