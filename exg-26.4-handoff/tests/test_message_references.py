"""Cases for the message references of table-driven validations: validate/MessageReferences.py and the EXG
numeric IDs in validate/MessageNumericId.py.

Three parts:
- unit cases for the section, edgarCode and code formatting, including entries carrying both efm and msgSection
  and the leading-guide setting;
- equivalence: the formatting sevMessage in validate/Filing.py did before the move (copied verbatim from
  ff7ba7e below) and the new functions give the same arguments, edgarCode and code for every entry of
  dei-validations.json and ft-validations.json, since no entry yet carries both references;
- numeric IDs: EFM and other codes keep theirs, EXG codes get the left-aligned range at the provisional base.

The numeric-ID part imports MessageNumericId, which needs Arelle: the plugin is expected at arelle/plugin/EDGAR
of an Arelle checkout, as in the stream's worktree.  Run with the Python that runs Arelle (it needs regex).
Usage: python3 test_message_references.py [path to EDGAR plugin checkout]   (or set EDGAR_PLUGIN)
"""
import importlib.util, json, os, string, sys

PLUGIN = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("EDGAR_PLUGIN", "."))
VALIDATE = os.path.join(PLUGIN, "validate")

def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(VALIDATE, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

mr = load("MessageReferences")
ok = True
def check(name, got, want):
    global ok
    good = got == want
    ok &= good
    print("PASS" if good else "FAIL", f"{name:60}", got if good else f"{got!r} != {want!r}")

# ---- unit cases

check("sectionCodeParts 6.5.2", mr.sectionCodeParts("6.5.2"), ["6", "05", "02"])
check("sectionCodeParts 3.1.24.2", mr.sectionCodeParts("3.1.24.2"), ["3", "01", "24", "02"])
check("sectionCodeParts 12.08", mr.sectionCodeParts("12.08"), ["12", "08"])
check("sectionCodeParts ft.oClmSrc", mr.sectionCodeParts("ft.oClmSrc"), ["ft", "oClmSrc"])

check("args efm only", mr.messageSectionArgs("6.5.20", None),
      {"efmSection": "60520", "arelleCode": "EFM.6.05.20"})
check("args ft efm", mr.messageSectionArgs("ft.oClmSrc", None),
      {"efmSection": "ftoClmSrc", "arelleCode": "EFM.ft.oClmSrc"})
check("args EXG only", mr.messageSectionArgs(None, "EXG:3.1.5"),
      {"exgSection": "30105", "arelleCode": "EXG.3.01.05"})
check("args both, EFM leads (the setting)", mr.messageSectionArgs("6.5.20", "EXG:3.1.5"),
      {"efmSection": "60520", "exgSection": "30105", "arelleCode": "EFM.6.05.20"})
check("args both, EXG leads", mr.messageSectionArgs("6.5.20", "EXG:3.1.5", leadingGuide="EXG"),
      {"efmSection": "60520", "exgSection": "30105", "arelleCode": "EXG.3.01.05"})
check("args EFM only, EXG leads", mr.messageSectionArgs("6.5.20", None, leadingGuide="EXG"),
      {"efmSection": "60520", "arelleCode": "EFM.6.05.20"})
check("args four-level EXG", mr.messageSectionArgs(None, "EXG:3.1.24.2"),
      {"exgSection": "3012402", "arelleCode": "EXG.3.01.24.02"})
check("args neither", mr.messageSectionArgs(None, None), {})
check("args empty efm", mr.messageSectionArgs("", None), {})
check("setting is EFM", mr.messageCodeLeadingGuide, "EFM")

key = "dq-{efmSection}-{tag}-Value"
check("edgarCode EFM code keeps -{efmSection}", mr.messageEdgarCode(key, "EFM.6.05.20"), key)
check("edgarCode EXG code drops -{efmSection}", mr.messageEdgarCode(key, "EXG.3.01.05"), "dq-{tag}-Value")
check("edgarCode no code", mr.messageEdgarCode(key, None), key)
check("edgarCode key without section", mr.messageEdgarCode("dq-Taxonomy-ns-Facts-Dependency", "EXG.3.05"),
      "dq-Taxonomy-ns-Facts-Dependency")

check("code EFM", mr.messageCode(key, {"arelleCode": "EFM.6.05.20", "efmSection": "60520", "tag": "DocumentType"}),
      "EFM.6.05.20.documentTypeValue")
check("code EXG", mr.messageCode(key, {"arelleCode": "EXG.3.01.05", "exgSection": "30105", "tag": "DocumentType"}),
      "EXG.3.01.05.documentTypeValue")
# the piece after the key's first hyphen is lowercased, which for this key is "ns", not "Taxonomy" (as before the move)
check("code key without section", mr.messageCode("dq-Taxonomy-ns-Facts-Dependency", {"arelleCode": "EXG.3.05"}),
      "EXG.3.05.TaxonomynsFactsDependency")
check("code removes commas, periods, spaces",
      mr.messageCode("dq-{efmSection}-{tags}-Missing", {"arelleCode": "EFM.6.05.20", "tags": "A, B.C D"}),
      "EFM.6.05.20.aBCDMissing")
check("code four-digit key", mr.messageCode("rq-0540-{tag}-Value", {"arelleCode": "EFM.6.05.40", "tag": "X"}),
      "EFM.6.05.40.xValue")
for name, args in (("code missing field raises KeyError", {"arelleCode": "EFM.6.05.20"}),
                   ("code missing arelleCode raises KeyError", {"tag": "X"})):
    try:
        mr.messageCode(key, args)
        check(name, "no exception", "KeyError")
    except KeyError:
        check(name, "KeyError", "KeyError")

# ---- equivalence with the formatting before the move, over every table entry

def oldFormatting(sev, messageKey, logArgs):
    """sevMessage's section and code formatting at ff7ba7e (validate/Filing.py 1231-1279), verbatim but for the
    error report, which is replaced by returning None."""
    import regex as re
    messageKeySectionPattern = re.compile(r"(.*[{]efmSection[}]|[a-z]{2}-[0-9]{4}|dq-)(.*)")
    if "efmSection" not in logArgs and not sev.get("msgSection"):
        logArgs["efmSection"] = sev.get("efm")
    if logArgs.get("efmSection"):
        efm = logArgs["efmSection"].split(".")
        logArgs["efmSection"] = ""
        logArgs["arelleCode"] = "EFM"
        for i, e in enumerate(efm):
            if i > 0 :
                if e.isnumeric(): # e.g. [6,5,2] -> "6.05.02"
                    e = e.zfill(2)
            logArgs["efmSection"] += e
            logArgs["arelleCode"] += "." + e

    # replacement for efmSection. Based on sev msgSection
    if sev.get("msgSection"):
        msgPrefix, _sep, msgSectionNumber = sev["msgSection"].partition(":")
        logArgs["arelleCode"] = msgPrefix
        section = f"{msgPrefix.lower()}Section"
        logArgs[section] = ""
        for i, e in enumerate(msgSectionNumber.split(".")):
            if i > 0 :
                if e.isnumeric(): # e.g. [6,5,2] -> "6.05.02"
                    e = e.zfill(2)
            logArgs["arelleCode"] += "." + e
            logArgs[section] += e

    logArgs["edgarCode"] = messageKey # edgar code is the un-expanded key for message with {...}'s
    if "-{efmSection}" in logArgs["edgarCode"] and not logArgs.get("efmSection") and logArgs.get("exgSection"):
        logArgs["edgarCode"] = logArgs["edgarCode"].replace("-{efmSection}", "")

    try:
        m = messageKeySectionPattern.match(messageKey or "")
        if m:
            keyAfterSection = m.group(2)
        else:
            keyAfterSection = ""
        arelleCode = "{arelleCode}.".format(**logArgs) + keyAfterSection.format(**logArgs) \
                      .replace(",", "").replace(".","").replace(" ","") # replace commas in names embedded in message code portion
        if arelleCode.endswith("."):
            arelleCode = arelleCode[:-1]
    except KeyError as err:
        return None
    arelleCodeSections = arelleCode.split("-")
    if len(arelleCodeSections) > 1 and arelleCodeSections[1]:
        arelleCodeSections[1] = arelleCodeSections[1][0].lower() + arelleCodeSections[1][1:] # start with lowercase
    arelleCode = "".join(arelleCodeSections)
    return arelleCode

def newFormatting(sev, messageKey, logArgs):
    """The same step as sevMessage now does it."""
    logArgs.update(mr.messageSectionArgs(logArgs.get("efmSection", sev.get("efm")), sev.get("msgSection")))
    logArgs["edgarCode"] = mr.messageEdgarCode(messageKey, logArgs.get("arelleCode"))
    try:
        return mr.messageCode(messageKey, logArgs)
    except KeyError:
        return None

def messageKeys(table, sev):
    """Every message key the entry can log: its own, its validation's, and the alternates sevMessage is given."""
    validation = table["validations"].get(sev.get("validation"), {})
    keys = {sev.get("message"), validation.get("message"), sev.get("elo-match-message")}
    keys |= {v for k, v in validation.items() if k.startswith("message") and isinstance(v, str)}
    return sorted(k for k in keys if k)

def fieldValues(messageKey):
    """A value for every {field} of the key other than the section fields, as a caller would pass."""
    return {f: "Some Name" for _t, f, _s, _c in string.Formatter().parse(messageKey)
            if f and not f.endswith("Section")}

compared = differing = 0
for tableName in ("dei-validations.json", "ft-validations.json"):
    table = json.load(open(os.path.join(VALIDATE, "resources", tableName), encoding="utf-8"))
    sevs = table["sub-type-element-validations"]
    both = sum("efm" in s and "msgSection" in s for s in sevs)
    check(f"{tableName}: no entry carries both yet", both, 0)
    for sev in sevs:
        for messageKey in messageKeys(table, sev):
            # the two ways sevMessage is called: efmSection passed from the entry, or left to sevMessage
            for passed in ({"efmSection": sev.get("efm")}, {}):
                old, new = dict(passed, **fieldValues(messageKey)), dict(passed, **fieldValues(messageKey))
                oldCode, newCode = oldFormatting(sev, messageKey, old), newFormatting(sev, messageKey, new)
                compared += 1
                if (oldCode, old) != (newCode, new):
                    differing += 1
                    if differing <= 5:
                        print("  differs", tableName, sev.get("validation"), messageKey, passed, oldCode, newCode, old, new)
check("equivalence: table entries x message keys x call forms compared", compared > 1000, True)
print(f"     {compared} compared")
check("equivalence: differing", differing, 0)

# an entry carrying both is where old and new are meant to differ: the EFM code stays, EXG is an added argument
sev = {"efm": "6.5.20", "msgSection": "EXG:3.1.5"}
old, new = {"efmSection": "6.5.20", "tag": "DocumentType"}, {"efmSection": "6.5.20", "tag": "DocumentType"}
check("both: before the change, EXG replaced the EFM code", oldFormatting(sev, key, old), "EXG.3.01.05.documentTypeValue")
check("both: now the EFM code stays", newFormatting(sev, key, new), "EFM.6.05.20.documentTypeValue")
check("both: now efmSection, exgSection and the EFM edgarCode",
      (new["efmSection"], new["exgSection"], new["edgarCode"]), ("60520", "30105", key))

# ---- numeric IDs

ARELLE = os.path.dirname(os.path.dirname(os.path.dirname(PLUGIN)))  # <arelle checkout>/arelle/plugin/EDGAR
sys.path.insert(0, ARELLE)
mn = load("MessageNumericId")
def numId(code):
    return mn.messageNumericId(None, "ERROR", code, {})[1]
check("id EFM.6.05.20.missingDocumentType unchanged", numId("EFM.6.05.20.missingDocumentType"), 26052000)
check("id EFM.6.05.40.xValue unchanged", numId("EFM.6.05.40.xValue"), 26054000)
check("id ix11.10.1.2 unchanged", numId("ix11.10.1.2"), 40010200)
check("id arelle:loadDeiValidations unknown", numId("arelle:loadDeiValidations"), mn.unknown)
check("id EXG.3.01.05.missingDocumentType", numId("EXG.3.01.05.missingDocumentType"), 103010500)
check("id EXG.12.08", numId("EXG.12.08"), 112080000)
check("id EXG.3.01.24.02.x (four levels)", numId("EXG.3.01.24.02.x"), 103012402)
check("id EXG.10.08.01.relationshipNotPermitted", numId("EXG.10.08.01.relationshipNotPermitted"), 110080100)
check("id EXG.3.05.TaxonomynsFactsDependency", numId("EXG.3.05.TaxonomynsFactsDependency"), 103050000)
check("id EXG five levels is unknown", numId("EXG.1.2.3.4.5.x"), mn.unknown)
check("id EXG level over 99 is unknown", numId("EXG.3.100.x"), mn.unknown)
check("id EXG base is provisional 100,000,000", mn.exgStart, 100000000)
check("id EXG range above every other range",
      mn.exgStart > max(mn.ftStart, mn.efmStart, mn.ixStart, mn.xbrlStart, mn.xml1Start, mn.xml2Start, mn.xml3Start, mn.unknown), True)
check("id EXG and EFM codes of one entry differ by the setting only",
      (numId(mr.messageSectionArgs("6.5.20", "EXG:3.1.5")["arelleCode"] + ".x"),
       numId(mr.messageSectionArgs("6.5.20", "EXG:3.1.5", leadingGuide="EXG")["arelleCode"] + ".x")),
      (26052000, 103010500))

# ---- the messageCodes parameter (hf-exg-message-codes)

if hasattr(mr, "parseMessageCodes"):
    check("messageCodes absent: EFM", mr.parseMessageCodes(None), ("EFM",))
    check("messageCodes blank-separated string", mr.parseMessageCodes("EXG EFM"), ("EXG", "EFM"))
    check("messageCodes JSON list, any case", mr.parseMessageCodes(["exg"]), ("EXG",))
    check("messageCodes empty string: EFM", mr.parseMessageCodes(""), ("EFM",))
    check("guides EXG EFM: code EXG when both references",
          mr.messageSectionArgs("6.5.20", "EXG:3.1.5", ("EXG", "EFM"))["arelleCode"], "EXG.3.01.05")
    check("guides EXG EFM: code EFM when only EFM",
          mr.messageSectionArgs("6.5.20", None, ("EXG", "EFM"))["arelleCode"], "EFM.6.05.20")
    check("guides EFM: unchanged from the setting",
          mr.messageSectionArgs("6.5.20", "EXG:3.1.5", ("EFM",)), mr.messageSectionArgs("6.5.20", "EXG:3.1.5"))
    key, base = "dq-{efmSection}-{tag}-Value", {"tag": "DocumentType"}
    def guideCodes(efm, msgSection, guides):
        a = dict(base, **mr.messageSectionArgs(efm, msgSection, guides))
        return mr.messageGuideCodes(key, a, efm, msgSection, guides)
    check("both codes as arguments (EXG EFM)", guideCodes("6.5.20", "EXG:3.1.5", ("EXG", "EFM")),
          {"exgCode": "EXG.3.01.05.documentTypeValue", "efmCode": "EFM.6.05.20.documentTypeValue"})
    check("only the references present (EXG EFM, EFM only)", guideCodes("6.5.20", None, ("EXG", "EFM")),
          {"efmCode": "EFM.6.05.20.documentTypeValue"})
    check("one guide listed: no extra arguments", guideCodes("6.5.20", "EXG:3.1.5", ("EXG",)), {})
    check("efmCode equals the code an EFM-coded run gives",
          guideCodes("6.5.20", "EXG:3.1.5", ("EXG", "EFM"))["efmCode"],
          mr.messageCode(key, dict(base, **mr.messageSectionArgs("6.5.20", "EXG:3.1.5"))))

# ---- efm-exg-references.json: EXG references for legacy checks with only an EFM reference

with open(os.path.join(VALIDATE, "resources", "efm-exg-references.json"), encoding="utf-8") as fh:
    resource = json.load(fh)
index = mr.referencesIndex(resource)
check("references resource indexes without conflicts", len(index), len(resource["references"]))
check("concepts: tag, prefixed", mr.messageConcepts({"tag": "EntityAddressAddressLine1"}, ["X"]), ["dei:EntityAddressAddressLine1"])
check("concepts: tags", mr.messageConcepts({"tags": "Security12bTitle, Security12gTitle"}, []),
      ["dei:Security12bTitle", "dei:Security12gTitle"])
check("concepts: entry names when no tag", mr.messageConcepts({}, ["oef:FundName"]), ["oef:FundName"])
check("principal office line 1 (6.5.48 r) -> 3.1.22.1",
      mr.inferredMsgSection(index, "6.5.48", "r", "", ["dei:EntityAddressAddressLine1"]), "EXG:3.1.22.1")
check("business contact line 1 (6.5.51 r, axis a) -> 3.2.1.2",
      mr.inferredMsgSection(index, "6.5.51", "r", "a", ["dei:EntityAddressAddressLine1"]), "EXG:3.2.1.2")
check("business contact phone (ruling) -> 3.2.1.4",
      mr.inferredMsgSection(index, "6.5.51", "r", "a", ["dei:LocalPhoneNumber"]), "EXG:3.2.1.4")
check("security axis (ruling) -> 3.2.4.1",
      mr.inferredMsgSection(index, "6.5.46", "security-axis", "c-or-required-context", ["dei:Security12bTitle"]), "EXG:3.2.4.1")
check("concepts in different sections: no reference",
      mr.inferredMsgSection(index, "6.5.51", "r", "a", ["dei:ContactPersonnelName", "dei:EntityAddressAddressLine1"]), None)
check("unmapped check: no reference", mr.inferredMsgSection(index, "6.5.99", "r", "", ["dei:X"]), None)
check("implicit absence: EntityShellCompany unexpected (6.5.21) -> its absence row 3.1.10",
      mr.inferredMsgSection(index, "6.5.21", "(unexpected)", "", ["dei:EntityShellCompany"]), "EXG:3.1.10")
check("implicit absence: business-contact phone unexpected (6.5.51) -> 3.2.1.4 (ruling)",
      mr.inferredMsgSection(index, "6.5.51", "(unexpected)", "", ["dei:LocalPhoneNumber"]), "EXG:3.2.1.4")
check("implicit absence: no EXG absence row in that context -> no reference",
      mr.inferredMsgSection(index, "6.5.51", "(unexpected)", "", ["dei:EntityAddressAddressLine2"]), None)
check("fee-tagging codes are never mapped", any(k[0].startswith("ft.") for k in index), False)
args = mr.messageSectionArgs("6.5.48", mr.inferredMsgSection(index, "6.5.48", "r", "", ["dei:EntityAddressAddressLine1"]))
check("default mode: EFM code, exgSection argument added", (args["arelleCode"], args["exgSection"]), ("EFM.6.05.48", "3012201"))
args = mr.messageSectionArgs("6.5.48", "EXG:3.1.22.1", ("EXG",))
check("EXG mode: EXG code", args["arelleCode"], "EXG.3.01.22.01")

print("ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
