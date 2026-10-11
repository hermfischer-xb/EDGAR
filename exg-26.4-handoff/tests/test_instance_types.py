"""Cases for EXG instance types: validate/InstanceTypes.py over validate/resources/exg-set-definitions.json (EXG 1.1 Set Definitions).

Three parts:
- the data: every Table 6-4 row names a submission set and entity sets that Tables 6-1 and 6-3 define, and every
  Table 6-1 suffix is one that Table 6-2 defines and the resolver can evaluate;
- submissions of each kind resolve to the instance types the guide's tables give, including the guide's own
  example (an FPI's F-3/A has an R33.FPI instance and may have an FE.A instance) and exhibit instances;
- the entitySets parameter decides when given, and a disagreement with the determined sets is reported.

InstanceTypes.py has no Arelle imports, so any Python 3 runs this.
Usage: python3 test_instance_types.py [path to EDGAR plugin checkout]   (or set EDGAR_PLUGIN)
"""
import importlib.util, json, os, sys

PLUGIN = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("EDGAR_PLUGIN", "."))
spec = importlib.util.spec_from_file_location("InstanceTypes", os.path.join(PLUGIN, "validate", "InstanceTypes.py"))
it = importlib.util.module_from_spec(spec)
spec.loader.exec_module(it)
with open(os.path.join(PLUGIN, "validate", "resources", "exg-set-definitions.json"), encoding="utf-8") as f:
    SETS = it.loadSetDefinitions(f)

ok = True
def check(name, got, want):
    global ok
    good = got == want
    ok &= good
    print("PASS" if good else "FAIL", f"{name:66}", got if good else f"{got!r} != {want!r}")

# ---- the data

subSets, entSets = set(SETS["submissionSets"]), set(SETS["entitySets"])
rows = SETS["instanceTypes"]
check("Table 6-4 rows name defined submission sets", sorted({r["submissionSet"] for r in rows} - subSets), [])
check("Table 6-4 rows name defined entity sets",
      sorted({e for r in rows for e in [r["includedEntitySet"]] + r["excludedEntitySets"]} - entSets), [])
usedSuffixes = {t[t.index(c):] for s in SETS["submissionSets"].values() for t in s["submissionTypes"]
                for c in "#%" if c in t}
check("Table 6-1 suffixes are defined in Table 6-2", sorted(usedSuffixes - set(SETS["submissionSetSuffixes"])), [])
check("every '%' suffix maps to exhibits", sorted(s for s in usedSuffixes if s[0] == "%" and s not in it.EXHIBIT_SUFFIXES), [])
check("every '#' suffix names a form",
      sorted(s for s in usedSuffixes if s[0] == "#" and not it.FORM_SUFFIX_MEANING.match(SETS["submissionSetSuffixes"][s])), [])

# ---- submissions

def types(submissionType, documentType=None, attachment=None, **kw):
    r = it.resolveInstanceTypes(SETS, submissionType, documentType, attachment, **kw)
    return r["instanceTypes"]

def submission(submissionType, documentType=None, attachment=None, **kw):
    return it.resolveInstanceTypes(SETS, submissionType, documentType, attachment, **kw)["submissionInstanceTypes"]

check("10-K", types("10-K", "10-K"), ["AF.US"])
check("10-K submission sets", sorted(it.submissionSetsOf(SETS, "10-K", "10-K")[0]), ["AF", "FAST"])
check("10-K/A submission sets", sorted(it.submissionSetsOf(SETS, "10-K/A", "10-K")[0]), ["AF", "AM", "FAST"])
check("10-K under an 814- file number", types("10-K", "10-K", fileNumbers=["814-01234"]), ["AF.BDC"])
check("10-Q under an 814- file number", types("10-Q", "10-Q", fileNumbers=["814-01234"]), ["QF.BDC"])
check("20-F", types("20-F", "20-F"), ["AF.FPI"])
check("40-F", types("40-F", "40-F"), ["AF.CA"])
check("N-CSR, investment company type N-1A", types("N-CSR", "N-CSR", invCompanyType="N-1A"), ["AF.OEF"])
check("N-CSR, investment company type N-2", types("N-CSR", "N-CSR", invCompanyType="N-2"), ["AF.CEF"])
check("N-CSR using cef facts, no type given", types("N-CSR", "N-CSR", taxonomyPrefixes={"cef"}), ["AF.CEF"])
check("N-CSRS", types("N-CSRS", "N-CSRS"), ["HF.OEF"])
check("10-Q", types("10-Q", "10-Q"), ["QF.US"])
check("SBSEF-FIN-QTR", types("SBSEF-FIN-QTR", "SBSEF-FIN-QTR"), ["QF.SEF"])
check("6-K", types("6-K", "6-K"), ["6K.FPI"])
check("8-K", types("8-K", "8-K"), ["8K.A"])
check("8-K, its Exhibit 98 instance", types("8-K", "EX-98", "EX-98"), ["EX98.SPAC"])
check("8-K with an Exhibit 98: the submission", submission("8-K", "EX-98", "EX-98"), ["8K.A", "EX98.SPAC"])
check("DEF 14A", types("DEF 14A", "DEF 14A"), ["PX.A"])
check("11-K (Table 6-1 writes 11K; corrected in the data)", types("11-K", "11-K"), ["EBP.A"])
check("S-1", types("S-1", "S-1"), ["R33.US"])
check("S-1, its fee exhibit instance", types("S-1", None, "EX-FILING FEES"), ["FE.A"])
check("S-11", types("S-11", "S-11"), ["R33.RT"])
check("S-6", types("S-6", "S-6"), ["R33.UIT"])
check("F-3/A (the guide's example)", types("F-3/A", "F-3"), ["R33.FPI"])
check("F-3/A, its fee exhibit (the guide's example)", types("F-3/A", None, "EX-FILING FEES"), ["FE.A"])
check("F-3/A fee exhibit: the submission", submission("F-3/A", None, "EX-FILING FEES"), ["FE.A", "R33.FPI"])
check("424B2", types("424B2", None, "EX-FILING FEES"), ["FE.A"])
check("424B2 primary document, no cef", types("424B2", "424B2"), ["PRO.ANC"])
check("424B2 primary document, cef facts", types("424B2", "424B2", taxonomyPrefixes={"cef"}), ["PRO.CEF"])
check("10-12B", types("10-12B", "10-12B"), ["R34.US"])
check("20FR12B", types("20FR12B", "20FR12B"), ["R34.FPI"])
check("40FR12B", types("40FR12B", "40FR12B"), ["R34.CA"])
check("Form 1 with EX.I.FORM1 (Table 6-4 names it AF.SRO)", types("1", "EX.I.FORM1", "EX.I.FORM1"), ["AF.SRO"])
check("N-8B-2", types("N-8B-2", "N-8B-2"), ["R40.UIT"])
check("485BPOS with an N-1A inside (#N1)", types("485BPOS", "N-1A"), ["RD.OEF"])
check("485BPOS with an N-4 inside (#N4)", types("485BPOS", "N-4"), ["RD.V4"])
check("485BPOS, its EX-99.4R HISTORIC instance", types("485BPOS", "EX-99.4R HISTORIC", "EX-99.4R HISTORIC"), ["RD.H99"])
check("485BPOS with no form named: no RD set", sorted(it.submissionSetsOf(SETS, "485BPOS", "485BPOS")[0]), [])
check("486BPOS with an N-2 inside (#N2)", types("486BPOS", "N-2"), ["RD.CEF"])
check("N-1A", types("N-1A", "N-1A"), ["RD.OEF"])
check("SD, its EX-2.01 instance (%201)", types("SD", "2.01 SD", "EX-2.01"), ["RXP.US"])
check("SD primary document: no OA set", sorted(it.submissionSetsOf(SETS, "SD", "SD")[0]), [])
check("SDR, its K SDR instance (%KL)", types("SDR", "K SDR", "EX-99.K SDR"), ["K.SDR"])
check("SDR, its L SDR instance", types("SDR", "L SDR", "EX-99.L SDR.INS"), ["L.SDR"])
check("17AD-27", types("17AD-27", "17AD-27"), ["OA.SRO"])
check("SBSEF-CCO-RPT", types("SBSEF-CCO-RPT", "SBSEF-CCO-RPT"), ["CCO.SEF"])
check("SBSEF-FIN-REQ", types("SBSEF-FIN-REQ", "SBSEF-FIN-REQ"), ["RF.SEF"])
check("SBSEF, its Exhibit I instance", types("SBSEF", "EX-99.I.SBSEF", "EX-99.I.SBSEF"), ["SE.FEX"])
check("SBSEF, its Exhibit C instance", types("SBSEF", "EX-99.C.SBSEF", "EX-99.C.SBSEF"), ["SE.OCX"])
check("SC TO-I primary document (R34 and TO, no SPAC)", types("SC TO-I", "SC TO-I"), ["R34.US"])
check("unknown submission type", types("X-99", "X-99"), [])
check("plugin form 'S-4EF§EX-98': its Exhibit 98 instance", types("S-4EF§EX-98", "EX-98", "EX-98"), ["EX98.SPAC"])
check("plugin form 'N-4§EX-99.4R HISTORIC'", types("N-4§EX-99.4R HISTORIC", "EX-99.4R HISTORIC", "EX-99.4R HISTORIC"), ["RD.H99"])
check("485BPOS, DocumentType 485BPOS, inv. company type N-1A", types("485BPOS", "485BPOS", invCompanyType="N-1A"), ["RD.OEF"])
check("497, DocumentType 497, inv. company type N-4", types("497", "497", invCompanyType="N-4"), ["RD.V4"])
check("485BPOS, nothing names the form: no instance type", types("485BPOS", "485BPOS"), [])
check("SC TO-C: TO set, but Table 6-4 has only its SPAC row", types("SC TO-C", "SC TO-C"), [])

# ---- the entitySets parameter

r = it.resolveInstanceTypes(SETS, "20-F", "20-F", entitySetsParameter="US")
check("parameter decides: 20-F given US", r["instanceTypes"], ["AF.US"])
check("parameter source", r["entitySetsSource"], "parameter")
check("disagreement (only parameter, only determined)", r["entitySetsDisagreement"], (["US"], ["FPI"]))
r = it.resolveInstanceTypes(SETS, "20-F", "20-F", entitySetsParameter=["FPI"])
check("parameter agreeing: no disagreement", r["entitySetsDisagreement"], None)
r = it.resolveInstanceTypes(SETS, "10-K", "10-K", entitySetsParameter="US XYZ")  # blank-separated, as from a formula parameter
check("unknown parameter code reported", r["unknownEntitySets"], ["XYZ"])
r = it.resolveInstanceTypes(SETS, "8-K", "8-K", entitySetsParameter=["US", "SPAC"])
check("parameter as a JSON list", sorted(r["entitySets"]), ["ALL", "SPAC", "US"])
check("8-K given US SPAC: only SPAC differs (US decides no 8K row)", r["entitySetsDisagreement"], (["SPAC"], []))
r = it.resolveInstanceTypes(SETS, "10-K", "10-K")
check("no parameter: determined", (r["entitySetsSource"], sorted(r["entitySets"])), ("determined", ["ALL", "US"]))

# ---- a document type standing in for the submission type (desktop preview without parameters)

check("K SDR previewed without parameters is an SDR's K exhibit", types("K SDR", "K SDR", "EX-99.K SDR"), ["K.SDR"])
check("L SDR previewed without parameters is an SDR's L exhibit", types("L SDR", "L SDR", "EX-99.L SDR"), ["L.SDR"])
check("2.01 SD previewed without parameters is an SD's exhibit",
      sorted(it.submissionSetsOf(SETS, "2.01 SD", "2.01 SD", "EX-2.01")[0]), ["OA"])

# ---- scope cells (Incl / Excl): parseScopeCell, scopeSubmissionSetsOf, scopeApplies

def cell(text):
    c = it.parseScopeCell(SETS, text)
    return sorted(c["s"]), sorted(c["i"]), c["all"], len(c["issues"])

check("cell s: and i: together", cell("s: AF, QF, i: AF.US, AF.BDC"), (["AF", "QF"], ["AF.BDC", "AF.US"], False, 0))
check("cell ALL", cell("i: ALL"), ([], [], True, 0))
check("cell instance type under s: counts, reported", cell("s: AF.CA"), ([], ["AF.CA"], False, 1))
check("cell set under i: counts, reported", cell("s: 8K, i: K.SDR, EBP"), (["8K", "EBP"], ["K.SDR"], False, 1))
check("cell missing commas read as meant, reported", cell("i: AF.FPI, R34.CA R33.FPI R33.US"),
      ([], ["AF.FPI", "R33.FPI", "R33.US", "R34.CA"], False, 1))
check("cell 'All' read as ALL, reported", cell("s: All"), ([], [], True, 1))
check("cell undefined code ignored, reported", cell("s: 6K, i: OA.SDR"), (["6K"], [], False, 1))

def scope(incl, excl, submissionType, documentType=None, attachment=None, **kw):
    r = it.resolveInstanceTypes(SETS, submissionType, documentType, attachment, **kw)
    return it.scopeApplies(SETS, incl, excl, r["scopeSubmissionSets"], r["instanceTypes"])

r = it.resolveInstanceTypes(SETS, "S-1", "S-1", "S-1")
check("S-1 primary document: not in FE for s:", ("FE" in r["scopeSubmissionSets"], "R33" in r["scopeSubmissionSets"]), (False, True))
r = it.resolveInstanceTypes(SETS, "S-1", None, "EX-FILING FEES")
check("S-1 fee exhibit: only FE for s:", (sorted(r["scopeSubmissionSets"]), r["instanceTypes"]), (["FE"], ["FE.A"]))
check("3.1.5 'i: ALL' excl 's: FE': S-1 primary in scope", scope("i: ALL", "s: FE", "S-1", "S-1", "S-1"), True)
check("3.1.5 'i: ALL' excl 's: FE': S-1 fee exhibit out", scope("i: ALL", "s: FE", "S-1", None, "EX-FILING FEES"), False)
check("8-K Exhibit 98 (SPAC) is not 's: 8K'", scope("s: 8K", "", "8-K", "EX-98", "EX-98", entitySetsParameter="SPAC"), False)
check("8-K Exhibit 98 (SPAC) is 'i: EX98.SPAC'", scope("i: EX98.SPAC", "", "8-K", "EX-98", "EX-98", entitySetsParameter="SPAC"), True)
check("8-K Exhibit 98 (SPAC) is 's: ALL'", scope("s: ALL", "", "8-K", "EX-98", "EX-98", entitySetsParameter="SPAC"), True)
r = it.resolveInstanceTypes(SETS, "SC TO-I", "EX-98", "EX-98", entitySetsParameter="SPAC")
check("SC TO-I Exhibit 98: in TO, which holds only exhibits", sorted(r["scopeSubmissionSets"]), ["TO"])
check("8-K primary is 's: 8K'", scope("s: 8K", "", "8-K", "8-K", "8-K"), True)
check("3.1.10 row 12 as drafted: EntityShellCompany absent on a 10-Q",
      scope("s: ALL", "i: AF.US, AF.BDC, AF.FPI", "10-Q", "10-Q", "10-Q"), True)
check("3.1.10 row 12 as drafted: not on a 10-K", scope("s: ALL", "i: AF.US, AF.BDC, AF.FPI", "10-K", "10-K", "10-K"), False)
check("487 (no submission set, no instance type) is not 's: ALL'", scope("s: ALL", "", "487", "S-6", "487"), False)

print("ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
