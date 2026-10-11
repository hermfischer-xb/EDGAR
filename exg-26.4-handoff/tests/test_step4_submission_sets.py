"""Step 4 of the required context ordering by EXG submission sets: the resolver's sets (InstanceTypes.py over
exg-set-definitions.json) and the EXG author's list (required-context.json) against the hand-kept copy they replace.

Until hf-exg-required-context-data, Consts.exgRequiredContextDurationSubmissionSets listed the submission types
for which step 4 applies.  This checks that every one of them still gets step 4, and that submission types outside
it do not.  The copy is reproduced below as it stood at hf-exg ab68415.

InstanceTypes.py has no Arelle imports, so any Python 3 runs this.
Usage: python3 test_step4_submission_sets.py [path to EDGAR plugin checkout]   (or set EDGAR_PLUGIN)
"""
import importlib.util, json, os, sys

PLUGIN = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("EDGAR_PLUGIN", "."))
V = os.path.join(PLUGIN, "validate")
spec = importlib.util.spec_from_file_location("InstanceTypes", os.path.join(V, "InstanceTypes.py"))
it = importlib.util.module_from_spec(spec); spec.loader.exec_module(it)
sets = json.load(open(os.path.join(V, "resources", "exg-set-definitions.json"), encoding="utf-8"))
step4 = set(json.load(open(os.path.join(V, "resources", "required-context.json"), encoding="utf-8"))
            ["durationSubmissionSets"]["sets"])

OLD = {  # Consts.exgRequiredContextDurationSubmissionSets at ab68415
    "6K":  {"6-K", "6-K/A"},
    "8K":  {"8-K", "8-K/A", "8-K12B", "8-K12B/A", "8-K12G3", "8-K12G3/A", "8-K15D5", "8-K15D5/A"},
    "AF":  {"10-K", "10-K/A", "10-KT", "10-KT/A", "20-F", "20-F/A", "40-F", "40-F/A",
            "N-CSR", "N-CSR/A", "SP 15D2", "SP 15D2/A"},
    "EBP": {"11-K", "11-K/A", "11-KT", "11-KT/A"},
    "HF":  {"N-CSRS", "N-CSRS/A"},
    "OA":  {"17AD-27", "17AD-27/A", "SD", "SD/A", "2.01 SD", "SDR", "SDR/A", "K SDR", "L SDR",
            "SBSEF-CCO-RPT", "SBSEF-CCO-RPT/A"},
    "QF":  {"10-Q", "10-Q/A", "10-QT", "10-QT/A", "SBSEF-FIN-QTR", "SBSEF-FIN-QTR/A"},
    "PX":  {"DEF 14A", "DEF 14C", "DEFA14A", "DEFA14C", "DEFC14A", "DEFC14C", "DEFM14A", "DEFM14C",
            "DEFR14A", "DEFR14C", "PRE 14A", "PRE 14C", "PREC14A", "PREC14C", "PREM14A", "PREM14C",
            "PRER14A", "PRER14C"},
    "RF":  {"SBSEF-FIN-REQ", "SBSEF-FIN-REQ/A"},
    "SE":  {"SBSEF", "SBSEF/A"},
    "TF":  {"10-KT", "10-KT/A", "10-QT", "10-QT/A", "11-KT", "11-KT/A"},
    "TO":  {"SC14D1F", "SC14D1F/A", "SC 14D9", "SC 14D9/A", "SC14D9C", "SC13E4F", "SC13E4F/A",
            "SC TO-I", "SC TO-I/A", "SC TO-C", "SC TO-C/A", "SC TO-T", "SC TO-T/A"},
}
# how the plugin sees the instance of these submissions: (submissionType, dei:DocumentType, attachmentDocumentType)
INSTANCE = {"SD": ("SD", "2.01 SD", "EX-2.01"), "SD/A": ("SD/A", "2.01 SD", "EX-2.01"),
            "2.01 SD": ("SD", "2.01 SD", "EX-2.01"),
            "SDR": ("SDR", "K SDR", "EX-99.K SDR"), "SDR/A": ("SDR/A", "L SDR", "EX-99.L SDR"),
            "K SDR": ("SDR", "K SDR", "EX-99.K SDR"), "L SDR": ("SDR", "L SDR", "EX-99.L SDR")}

def applies(submissionType):
    s, d, a = INSTANCE.get(submissionType, (submissionType, submissionType, submissionType))
    return bool(set(it.submissionSetsOf(sets, s, d, a)[0]) & step4)

ok = True
def check(name, got, want):
    global ok
    good = got == want; ok &= good
    print("PASS" if good else "FAIL", f"{name:60}", got if good else f"{got!r} != {want!r}")

check("the EXG author's step 4 sets", sorted(step4), sorted(OLD))
for setCode, types in OLD.items():
    missing = sorted(t for t in types if not applies(t))
    check(f"{setCode}: every submission type gets step 4", missing, [])
for t in ("S-1", "S-1/A", "F-1", "424B2", "485BPOS", "497", "N-1A", "10-12B", "SC 13D", "POS AM", "S-8"):
    check(f"{t}: no step 4", applies(t), False)
# Without parameters the plugin infers the submission type of a K or L SDR exhibit as the document type "K SDR",
# which Table 6-1 does not list.  The resolver maps it to SDR (InstanceTypes.DOCUMENT_TYPE_SUBMISSION_TYPES, on
# hf-exg-scope-cells), so such an exhibit is in OA and gets step 4, as the hand-kept copy's "K SDR"/"L SDR" did.
check("a K SDR exhibit previewed without parameters gets step 4",
      bool(set(it.submissionSetsOf(sets, "K SDR", "K SDR", "EX-99.K SDR")[0]) & step4), True)
check("an L SDR exhibit previewed without parameters gets step 4",
      bool(set(it.submissionSetsOf(sets, "L SDR", "L SDR", "EX-99.L SDR")[0]) & step4), True)

print("ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
