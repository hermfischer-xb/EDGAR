"""Add EXG-mode twins to an EFM conformance-suite testcase file, for the proposed dual-mode suite.

For each variation that expects a failure (<conf:assert num="60520" name="DocumentType" .../>), a twin is added
right after it: id "<id>-exg", the same data, "messageCodes": "EXG" added to its ELOparams, and an assert whose num
is the EXG code prefix the check would carry in EXG mode (num="EXG.3.01.05"; Arelle matches an EXG num as a code
prefix).  The EXG section comes from efm-exg-references.json: every reference for the assert's EFM section and
concept must give the same section, or the variation gets no twin and is reported.  An assert that already expects
an EXG code, or names no mapped concept, gets no twin either; the run shows those as EFM-coded in EXG mode.

The original variations are kept unchanged, so one run checks both modes.  The output can be written beside the
original (same relative instance paths) or elsewhere with --absolute, which rewrites data URIs to absolute paths.

Usage: python3 makeExgTwins.py <testcase.xml> <efm-exg-references.json> <out.xml> [--absolute]
"""
import collections, copy, json, os, re, sys
import xml.etree.ElementTree as ET

CONF = "http://edgar/2009/conformance"


def efmSection(num):
    """60520 -> 6.5.20; 605580 style six-digit numbers are not EFM 6.x.y sections handled here."""
    m = re.fullmatch(r"(\d)(\d\d)(\d\d)", num or "")
    return "{}.{}.{}".format(m.group(1), int(m.group(2)), int(m.group(3))) if m else None


def exgPrefix(section):
    parts = section.split(".")
    return "EXG." + ".".join([parts[0]] + [p.zfill(2) for p in parts[1:]])


def main(testcasePath, referencesPath, outPath, absolute=False):
    refs = json.load(open(referencesPath, encoding="utf-8"))["references"]
    byEfmConcept = collections.defaultdict(set)
    for r in refs:
        byEfmConcept[(r["efm"], r["concept"])].add(r["exg"])
    ET.register_namespace("conf", CONF)
    for prefix, uri in re.findall(r'xmlns:(\w+)="([^"]+)"', open(testcasePath, encoding="utf-8", errors="replace").read()):
        if prefix != "conf":
            ET.register_namespace(prefix, uri)
    tree = ET.parse(testcasePath)
    root = tree.getroot()
    base = os.path.dirname(os.path.abspath(testcasePath))
    made, skipped = 0, []
    children = list(root)
    for v in children:
        if v.tag != "{%s}variation" % CONF:
            continue
        if absolute:
            for d in v.iter():
                if d.tag in ("{%s}instance" % CONF, "{%s}schema" % CONF, "{%s}linkbase" % CONF) and d.text:
                    d.text = os.path.join(base, d.text.strip())
        asserts = v.findall(".//{%s}assert" % CONF)
        if not asserts:
            continue
        a = asserts[0]
        efm = efmSection(a.get("num"))
        concept = a.get("name") or ""
        concept = concept if ":" in concept else "dei:" + concept
        sections = byEfmConcept.get((efm, concept), set()) if efm else set()
        if len(sections) != 1:
            skipped.append((v.get("id"), a.get("num"), a.get("name"), "no reference" if not sections else "several: " + ", ".join(sorted(sections))))
            continue
        twin = copy.deepcopy(v)
        twin.set("id", v.get("id") + "-exg")
        for nm in twin.iter("{%s}name" % CONF):
            nm.text = "EXG mode: " + (nm.text or "")
            break
        params = [p for p in twin.iter("{%s}parameter" % CONF) if p.get("name") == "ELOparams"]
        if params:
            elo = json.loads(params[0].get("value"))
            elo["messageCodes"] = "EXG"
            params[0].set("value", json.dumps(elo))
        else:
            data = twin.find("{%s}data" % CONF)
            p = ET.SubElement(data, "{%s}parameter" % CONF, {"name": "ELOparams", "datatype": "xs:string",
                                                             "value": json.dumps({"messageCodes": "EXG"})})
            data.remove(p)
            data.insert(0, p)
        ta = twin.findall(".//{%s}assert" % CONF)[0]
        ta.set("num", exgPrefix(next(iter(sections))))
        root.insert(list(root).index(v) + 1, twin)
        made += 1
    tree.write(outPath, encoding="utf-8", xml_declaration=True)
    print("{}: {} twins; {} failing variations without a twin".format(os.path.basename(testcasePath), made, len(skipped)))
    for s in skipped:
        print("  no twin:", *s)


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    main(*sys.argv[1:4], absolute=len(sys.argv) == 5 and sys.argv[4] == "--absolute")
