"""documentPeriodEndDateRequired against the plugin's own dei-validations.json, compiled by its own loader.

Checks the forms the reply of 2026-09-20 names as making dei:DocumentPeriodEndDate optional, forms that require
it, and forms the table does not mention, then lists every submission type the table knows for which the fact
comes out optional, so that any other form the rule would affect is visible.
Run with the Arelle worktree as the working directory (it needs Arelle importable):
    python3 test_document_period_end_date_required.py <worktree root>
"""
import os, sys
root = sys.argv[1] if len(sys.argv) > 1 else "."
sys.path.insert(0, os.path.abspath(root))

from arelle import Cntlr
from arelle.plugin.EDGAR.validate.Util import loadDeiValidations
from arelle.plugin.EDGAR.validate.RequiredContext import documentPeriodEndDateRequired

cntlr = Cntlr.Cntlr(logFileName="logToBuffer")
errors = []
class EveryConcept:
    """Keeps every entry: the loader drops names absent from the filing's taxonomy."""
    def __contains__(self, qn): return True
class DeiDoc:
    targetNamespace = "http://xbrl.sec.gov/dei/2025"
class ModelXbrlStub:
    """Only what loadDeiValidations reads from a model."""
    modelManager = cntlr.modelManager
    prefixedNamespaces = {"dei": DeiDoc.targetNamespace}
    urlDocs = {"dei": DeiDoc()}
    qnameConcepts = EveryConcept()
    def error(self, code, msg, **kw): errors.append((code, msg % kw if kw else msg))
    def warning(self, code, msg, **kw): errors.append((code, msg % kw if kw else msg))
validations = loadDeiValidations(ModelXbrlStub(), True, None)
assert not errors, errors
sevs = validations["sub-type-element-validations"]
required = lambda subType, docType=None: documentPeriodEndDateRequired(sevs, "DocumentPeriodEndDate", subType, docType, None)

cases = [(t, False) for t in ("DEF 14A", "DEF 14C", "PRE 14A", "PRE 14C", "PREM14A", "PREM14C",
                              "POS AM", "POS EX", "11-K", "11-K/A", "11-KT", "11-KT/A")]
cases += [(t, True) for t in ("10-K", "10-K/A", "10-Q", "10-QT", "8-K", "20-F", "40-F", "6-K", "N-CSR", "N-CSRS",
                              "SD", "17AD-27", "S-6")]
cases += [(t, True) for t in ("S-1", "424B2", "F-3")]  # not in any DocumentPeriodEndDate entry: 4b unchanged
ok = True
for subType, expected in cases:
    got = required(subType)
    ok &= got == expected
    print("PASS" if got == expected else "FAIL", f"{subType:10} required={got}")

# every submission type the table knows, to show exactly which ones the restriction reaches
known = set()
for sev in sevs:
    known |= {t for t in sev.get("subTypeSet", ()) if t not in ("all", "n/a", "!not!")}
optional = sorted(t for t in known if not required(t))
print(f"\nsubmission types for which dei:DocumentPeriodEndDate is optional ({len(optional)} of {len(known)} known):")
print("  " + ", ".join(optional))
print("ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
