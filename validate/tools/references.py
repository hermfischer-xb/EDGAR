"""Candidate EXG references for the legacy checks, for review: the input to efm-exg-references.json.

For each legacy family (crosswalk.py's families of dei-validations.json entries) and each concept it checks, the
EXG section 3 section whose code the check would carry in EXG mode.  A message code takes the section, not the row,
so a concept whose candidate rows all lie in one section is settled even when the row is not.

Candidates, by the rulings in resources/exg/handoffs/mapping-rulings.md:
  1. rows that bind the concept and cite the family's EFM section (in the "EFM v68 Ref" cell);
  2. not 3.1.1, which creates no checks, and not "A {n} fact is absent." rows, which belong to the legacy file's
     implicit absence check (crosswalk.py's unexpectedFamilies), not to these families;
  3. rows whose context class (the "c" column) is compatible with the legacy entry's axis binding.  The axis key
     is only a filter here: no axis binds undimensioned contexts (the required context, or any undimensioned one,
     depending on the check), so it is compatible with r, se and a; "a" (business contact or US agent) with bc and
     a; "f" (former address) with fa and a; "oef:class" with cc and a; the class-of-stock keys with r, se and a;
  4. where several sections remain, narrowed in turn, each step applied only when it leaves something:
     a. rows whose EFM cell code is the legacy validation code ("oph" stays on the all-contexts "neither or both"
        row it is);
     b. rows in a specific context class over all-contexts (c = a) rows;
     c. rows where the concept is the subject of the check, not a condition: in "If ... then ...", the concepts
        after "then"; otherwise every concept the check names;
     d. the concept's home section: rows that check that concept alone;
     e. rows whose Incl scope shares an instance type with the legacy family's gate;
  5. a ruling in mapping-rulings.md, where one exists (RULINGS below), overrides the above.

Tiers in the output: "code" (one section, and the row's EFM cell code is the legacy validation code), "section" (one
section, EFM section agrees but the cell code does not), "ruling", "several" (for review), "none" (unlinked).

Also written: absence-candidates.tsv, for the legacy file's implicit absence check.  Filing.py reports a concept
unexpected (from a "(blank)" or "(blank-error)" entry) with the EFM section of the entries that name the concept
for that context; EXG states the same check as "A {n} fact is absent." rows.  Each (EFM section of an entry naming
the concept, concept) maps to the section of the concept's absence row in a context compatible with that entry's
axis key, with the business-contact phone ruled to 3.2.1.4 as for the other checks.

Usage: python3 references.py <crosswalk out dir with crosswalk.json> <guide.json> <plugin validate dir> <out dir>
"""
import collections, csv, json, os, re, sys

# rulings recorded in resources/exg/handoffs/mapping-rulings.md: (EFM section, legacy validation code, concept or "*") -> EXG section
RULINGS = {
    ("6.5.46", "security-axis", "*"): "3.2.4.1",
    ("6.5.46", "ot1", "*"): "3.2.4.1",
    ("6.5.46", "te", "*"): "3.2.4.3",
    ("6.5.46", "t1", "*"): "3.2.4.4",
    # N-2: registration flags and file numbers are 3.1.24.1, amendments 3.1.24.2
    ("6.5.55", "n2c", "dei:DocumentRegistrationStatement"): "3.1.24.1",
    ("6.5.55", "n2c", "dei:InvestmentCompanyActRegistration"): "3.1.24.1",
    ("6.5.55", "o", "dei:DocumentRegistrationStatement"): "3.1.24.1",
    ("6.5.55", "o", "dei:InvestmentCompanyActRegistration"): "3.1.24.1",
    ("6.5.55", "ov", "dei:DocumentRegistrationStatement"): "3.1.24.1",
    # business-contact phone: 3.2.1.4 "Phone", where the area code is checked with it (review, 2026-10-10)
    ("6.5.51", "r", "dei:LocalPhoneNumber"): "3.2.1.4",
    ("6.5.51", "o", "dei:LocalPhoneNumber"): "3.2.1.4",
}

COMPATIBLE = {
    "": {"r", "se", "a", ""},
    "a": {"bc", "a"},
    "f": {"fa", "a"},
    "oef:class": {"cc", "a"},
    "c": {"r", "se", "a", ""},
    "c-or-required-context": {"r", "se", "a", ""},
}


def subjectSlots(check):
    """{n} slots a check is about: after "then" in an "If ... then ..." check, else all of them."""
    m = re.match(r"\s*If\b.*?\bthen\b(.*)$", check, re.S | re.I)
    return set(re.findall(r"\{\d+\}", m.group(1) if m else check))


def typesOf(described, sets):
    """Instance types from crosswalk.describeTypes' "s: AF, QF; i: 8K.A" form."""
    bySet = collections.defaultdict(set)
    for r in sets["instanceTypes"]:
        bySet[r["submissionSet"]].add(r["instanceType"])
    out = set()
    for part in described.split(";"):
        kind, _, codes = part.strip().partition(":")
        for code in (c.strip() for c in codes.split(",") if c.strip()):
            out |= bySet[code] if kind.strip() == "s" else {code}
    return out


def rowTypes(row, sets):
    """Instance types a row's Incl cell names (submission sets expanded; ALL is every instance type)."""
    cell = row["incl"]
    if cell["all"]:
        return {r["instanceType"] for r in sets["instanceTypes"]}
    out = set(cell["i"])
    for r in sets["instanceTypes"]:
        if r["submissionSet"] in cell["s"]:
            out.add(r["instanceType"])
    return out


def main(crosswalkDir, guidePath, validateDir, outDir):
    with open(os.path.join(crosswalkDir, "crosswalk.json")) as fh:
        cw = json.load(fh)
    with open(guidePath) as fh:
        guide = json.load(fh)
    with open(os.path.join(validateDir, "resources", "dei-validations.json")) as fh:
        dei = json.load(fh)
    with open(os.path.join(validateDir, "resources", "exg-set-definitions.json")) as fh:
        sets = json.load(fh)
    import importlib.util
    spec = importlib.util.spec_from_file_location("InstanceTypes", os.path.join(validateDir, "InstanceTypes.py"))
    IT = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(IT)
    entries = dei["sub-type-element-validations"]
    concepts = collections.defaultdict(dict)
    for c in guide["concepts"]:
        concepts[c["Section"]][c["Elt"].strip()] = c["Concept"].strip()
    rows = []
    for v in guide["validations"]:
        sec = v["Section"]
        if not sec.startswith("3.") or sec == "3.1.1" or v.get("rowDeleted"):
            continue
        check = (v.get("Check") or v.get("Assertion") or "").replace("\n", " ").strip()
        if re.match(r"^A \{\d+\} fact is absent\.?$", check):
            continue
        refs = (v.get("EFM v68 Ref") or v.get("Ref") or "").replace("\xa0", " ")
        text = check + " " + (v.get("On failure") or "")
        slots = set(re.findall(r"\{\d+\}", text))
        rows.append({"section": sec, "row": v["Row"], "c": (v.get("c") or "").strip(), "check": check,
                     "incl": IT.parseScopeCell(sets, v.get("Incl") or v.get("Types") or ""),
                     "bound": {concepts[sec].get(n): n for n in slots if concepts[sec].get(n)},
                     "subjects": {concepts[sec].get(n) for n in subjectSlots(check) if concepts[sec].get(n)},
                     "refSections": re.findall(r"§\s*([\d.]+\d)", refs),
                     "codes": [t.strip() for t in re.split(r"[,;]", re.sub(r"§\s*[\d.]+", "", refs)) if t.strip()]})
    titles = guide["sections"]

    out = []
    for f in cw["families"]:
        if f["file"] != "dei" or f["msgSection"]:
            continue
        sev = entries[f["entries"][0]]
        axis = sev.get("axis", "")
        compatible = COMPATIBLE.get(axis, {"r", "se", "a", ""})
        val = (f["validation"] or "").lower()
        for name in f["names"].split():
            cand = [r for r in rows if name in r["bound"] and f["efm"] and f["efm"] in r["refSections"]]
            ctx = [r for r in cand if r["c"] in compatible]
            sectionsBeforeNarrowing = len({r["section"] for r in ctx})
            familyTypes = typesOf(f["instanceTypes"], sets)
            codesOf = lambda r: {c.lower() for c in r["codes"]} | {c.lower().rstrip("*") for c in r["codes"]}
            for narrow in (lambda r: val in codesOf(r),
                           lambda r: r["c"] != "a",
                           lambda r: name in r["subjects"],
                           lambda r: set(r["bound"]) == {name},
                           lambda r: bool(rowTypes(r, sets) & familyTypes)):
                if len({r["section"] for r in ctx}) <= 1:
                    break
                kept = [r for r in ctx if narrow(r)]
                if kept:
                    ctx = kept
            secs = sorted({r["section"] for r in ctx})
            ruling = RULINGS.get((f["efm"], f["validation"], name)) or RULINGS.get((f["efm"], f["validation"], "*"))
            if ruling:
                tier, chosen = "ruling", ruling
            elif not cand:
                tier, chosen = "none", ""
            elif len(secs) == 1:
                codeMatch = any(val in {c.lower() for c in r["codes"]} | {c.lower().rstrip("*") for c in r["codes"]}
                                for r in ctx if r["section"] == secs[0])
                tier, chosen = ("code" if codeMatch else "section"), secs[0]
            elif not secs:
                tier, chosen = "several", ""  # candidates, but none in a compatible context
            else:
                tier, chosen = "several", ""
            out.append({
                "family": f["id"], "entries": " ".join(map(str, f["entries"])), "efm": f["efm"], "validation": f["validation"],
                "axis": axis, "concept": name, "tier": tier, "exgSection": chosen,
                "sectionsBeforeNarrowing": sectionsBeforeNarrowing, "familyInstanceTypes": f["instanceTypes"],
                "exgTitle": titles.get(chosen, ""),
                "efmCodePrefix": "EFM." + ".".join(p.zfill(2) if i else p for i, p in enumerate(f["efm"].split("."))) if f["efm"] else "",
                "exgCodePrefix": "EXG." + ".".join(p.zfill(2) if i else p for i, p in enumerate(chosen.split("."))) if chosen else "",
                "candidates": " | ".join("{}#{} c={} {}".format(r["section"], r["row"], r["c"], r["check"][:70])
                                         for r in (ctx if chosen or secs else cand)),
                "otherContexts": " | ".join("{}#{} c={}".format(r["section"], r["row"], r["c"]) for r in cand if r not in ctx),
            })

    os.makedirs(outDir, exist_ok=True)
    cols = list(out[0])
    with open(os.path.join(outDir, "candidates.tsv"), "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(cols)
        for r in out:
            w.writerow([r[c] for c in cols])
    tiers = collections.Counter(r["tier"] for r in out)
    print(len(out), "family-concept pairs:", dict(tiers))
    with open(os.path.join(outDir, "candidates.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    writeSpotCheck(out, dei, os.path.join(outDir, "spot-check.md"))
    writeAbsence(guide, concepts, entries, os.path.join(outDir, "absence-candidates.tsv"))


def normaliseNames(names):
    """An entry's xbrl-names as prefixed concepts (dei: when unprefixed)."""
    names = names if isinstance(names, list) else [names]
    return [n if ":" in n else "dei:" + n for n in names if isinstance(n, str)]


ABSENCE_RULINGS = {("dei:LocalPhoneNumber", "a"): "3.2.1.4"}  # as RULINGS: the business-contact phone is 3.2.1.4


def writeAbsence(guide, concepts, entries, path):
    """Implicit absence: (EFM section, concept) of a legacy "unexpected" message -> EXG absence-row section."""
    absent = collections.defaultdict(list)
    for v in guide["validations"]:
        sec = v["Section"]
        if not sec.startswith("3.") or sec == "3.1.1" or v.get("rowDeleted"):
            continue
        m = re.match(r"^A (\{\d+\}) fact is absent\.?$", (v.get("Check") or v.get("Assertion") or "").strip())
        if m and concepts[sec].get(m.group(1)):
            absent[concepts[sec][m.group(1)]].append((sec, v["Row"], (v.get("c") or "").strip()))
    pairs = collections.OrderedDict()  # (efm, concept) -> set of axis keys
    for e in entries:
        if e.get("validation") in (None, "fany") or all(k.startswith("comment") for k in e) or not e.get("efm"):
            continue
        for n in normaliseNames(e.get("xbrl-names", e.get("xbrl-name"))):
            pairs.setdefault((e["efm"], n), set()).add(e.get("axis", ""))
    rows = []
    for (efm, name), axes in pairs.items():
        if name not in absent:
            continue
        secs, used = set(), []
        for axis in sorted(axes):
            ruling = ABSENCE_RULINGS.get((name, axis))
            cand = [r for r in absent[name] if r[2] in COMPATIBLE.get(axis, {"r", "se", "a", ""})]
            if ruling:
                secs.add(ruling); used += [r for r in cand if r[0] == ruling]
            else:
                secs |= {r[0] for r in cand}; used += cand
        tier = "absence" if len(secs) == 1 else ("several" if secs else "none")
        rows.append([efm, "(unexpected)", "", name, tier, ",".join(sorted(secs)) if tier != "absence" else secs.pop(),
                     " | ".join("{}#{} c={}".format(*r) for r in used), " ".join(sorted(axes))])
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["efm", "validation", "axis", "concept", "tier", "exgSection", "candidates", "legacyAxes"])
        w.writerows(rows)
    print(len(rows), "absence pairs:", dict(collections.Counter(r[4] for r in rows)))


def writeSpotCheck(out, dei, path):
    """The settled pairs by EXG section, for review."""
    legend = {k: (v.get("validation") or "")[:70] for k, v in dei["validations"].items()}
    settled = [r for r in out if r["tier"] in ("code", "section", "ruling")]
    bySection = collections.defaultdict(list)
    for r in settled:
        bySection[r["exgSection"]].append(r)
    lines = ["# Spot-check list: legacy checks and the EXG section whose code each would carry", "",
             "For review. Each line is one legacy check (a family of `dei-validations.json` entries) and one concept "
             "it checks, with the EDGAR XBRL Guide section 3 section whose code the check's message would carry in "
             "EXG mode: the code prefix changes from the EFM section's to the EXG section's, and the rest of the "
             "code (the message key) stays.",
             "",
             "Tiers: **code**, one section and the row's EFM cell code is the legacy validation code; **section**, "
             "one section and the EFM section agrees; **ruling**, decided in "
             "`validate/resources/exg/handoffs/mapping-rulings.md`. Rows: the EXG rows that decided it.", "",
             "{} of {} family-concept pairs; the rest are in README.md.".format(len(settled), len(out)), ""]
    for sec in sorted(bySection, key=lambda s: [int(x) for x in s.split(".")]):
        rs = bySection[sec]
        lines.append("## {} {} ({})\n".format(sec, rs[0]["exgTitle"], rs[0]["exgCodePrefix"]))
        lines.append("| Legacy entries | EFM | Validation | Concept | Tier | Rows |\n|---|---|---|---|---|---|")
        for r in sorted(rs, key=lambda r: (r["efm"], r["family"], r["concept"])):
            rows = ", ".join(x.split(" c=")[0] for x in r["candidates"].split(" | ") if x)
            lines.append("| {} | {} | `{}` {} | {} | {} | {} |".format(r["entries"], r["efm"], r["validation"],
                         legend.get(r["validation"], ""), r["concept"], r["tier"], rows))
        lines.append("")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
