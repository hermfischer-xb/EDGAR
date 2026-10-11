"""Add EXG-mode twins to an EFM conformance-suite testcase file, for the proposed dual-mode suite.

For each variation that expects a failure (<conf:assert num="60520" name="DocumentType" .../>), a twin is added
right after it: id "<id>-exg", the same data, "messageCodes": "EXG" added to its ELOparams, and an assert whose num
is the EXG code prefix the check would carry in EXG mode (num="EXG.3.01.05"; Arelle matches an EXG num as a code
prefix).  The EXG section comes either
  - with --observed <logs>, from a legacy-mode run of the suite on a plugin that reads efm-exg-references.json: the
    exgSection argument of the messages, for that variation's instance, whose code begins with the assert's EFM
    code.  That is exactly the section the plugin's lookup gives the message, so it is the precise source; or
  - otherwise, from efm-exg-references.json by the assert's EFM section and concept alone, which is ambiguous where
    one concept is checked by several legacy validations in different sections.
When the source gives no section, or more than one, the variation gets no twin and is reported.  An assert that already expects
an EXG code, or names no mapped concept, gets no twin either; the run shows those as EFM-coded in EXG mode.

The original variations are kept unchanged, so one run checks both modes.  The output can be written beside the
original (same relative instance paths) or elsewhere with --absolute, which rewrites data URIs to absolute paths.

Usage: python3 makeExgTwins.py <testcase.xml> <efm-exg-references.json> <out.xml> [--absolute] [--observed <dir of *.log.xml>]
"""
import collections, copy, html, json, os, re, sys
import xml.etree.ElementTree as ET

CONF = "http://edgar/2009/conformance"


def efmSection(num):
    """60520 -> 6.5.20; 605580 style six-digit numbers are not EFM 6.x.y sections handled here."""
    m = re.fullmatch(r"(\d)(\d\d)(\d\d)", num or "")
    return "{}.{}.{}".format(m.group(1), int(m.group(2)), int(m.group(3))) if m else None


def exgPrefix(section):
    parts = section.split(".")
    return "EXG." + ".".join([parts[0]] + [p.zfill(2) for p in parts[1:]])


def observedSections(logPaths):
    """{instance file name: [(code, tag, exgSection)]} from Arelle XML logs of a legacy-mode suite run.  A log entry's
    ref is the instance's file name, which in the EFM suite is unique (it encodes the variation)."""
    out = collections.defaultdict(list)
    for path in logPaths:
        # an Arelle XML log file can hold several <log> documents one after another (it appends), so wrap them
        text = re.sub(r"<\?xml[^>]*\?>", "", open(path, encoding="utf-8", errors="replace").read())
        for entry in ET.fromstring("<logs>" + text + "</logs>").iter("entry"):
            code = entry.get("code") or ""
            msg, ref = entry.find("message"), entry.find("ref")
            if not code.startswith("EFM.") or msg is None or ref is None or not msg.get("exgSection"):
                continue
            out[os.path.basename((ref.get("href") or "").partition("#")[0])].append((code, msg.get("tag") or msg.get("tags") or "", msg.get("exgSection")))
    return out


def restoreNamespaceDeclarations(originalPath, outPath):
    """ElementTree drops namespace declarations that only text content uses, such as xmlSchema in an expected error
    written as a QName (<error>xmlSchema:valueError</error>); put the original root's declarations back."""
    original = open(originalPath, encoding="utf-8", errors="replace").read()
    rootTag = re.search(r"<(?![?!])[^>]*>", original)
    decls = dict(re.findall(r'xmlns:(\w[\w.-]*)="([^"]*)"', rootTag.group(0))) if rootTag else {}
    text = open(outPath, encoding="utf-8").read()
    m = re.search(r"<(?![?!])[^>]*?(/?)>", text)
    present = set(re.findall(r'xmlns:(\w[\w.-]*)=', m.group(0)))
    missing = "".join(' xmlns:{}="{}"'.format(k, v) for k, v in decls.items() if k not in present)
    if missing:
        end = m.end() - (2 if m.group(1) else 1)
        text = text[:end] + missing + text[end:]
        with open(outPath, "w", encoding="utf-8") as fh:
            fh.write(text)


def insertTwinsAsText(text, twins):
    """The testcase file's own text with a twin of each listed variation inserted after it, so that a merge into the
    suite source shows only added lines.  twins: [(variation id, EXG code prefix)]."""
    for vid, prefix in twins:
        m = re.search(r'(?P<indent>[ \t]*)(?P<block><(?P<p>\w+:)?variation\b[^>]*\bid="{}"[^>]*>.*?</(?P=p)?variation>)'
                      .format(re.escape(vid)), text, re.S)
        if not m:
            raise ValueError("variation {} not found as text".format(vid))
        block, pfx, indent = m.group("block"), m.group("p") or "", m.group("indent")
        twin = re.sub(r'\bid="{}"'.format(re.escape(vid)), 'id="{}-exg"'.format(vid), block, count=1)
        elo = re.search(r'(<{}parameter\b[^>]*\bname="ELOparams"[^>]*\bvalue=")([^"]*)(")'.format(pfx), twin)
        if elo:
            value = json.loads(html.unescape(elo.group(2)))
            value["messageCodes"] = "EXG"
            twin = twin[:elo.start(2)] + html.escape(json.dumps(value), quote=True).replace("&#x27;", "'") + twin[elo.end(2):]
        else:
            data = re.search(r'<{}data\b[^>]*>(\s*)'.format(pfx), twin)
            param = '<{}parameter name="ELOparams" datatype="xs:string" value="{{&quot;messageCodes&quot;: &quot;EXG&quot;}}"/>'.format(pfx)
            twin = twin[:data.end(0) - len(data.group(1))] + data.group(1) + param + data.group(1) + twin[data.end(0):]
        twin = re.sub(r'(<{}name>)'.format(pfx), r'\1EXG mode: ', twin, count=1)
        twin = re.sub(r'(<{}assert\b[^>]*\bnum=")[^"]*(")'.format(pfx), r'\g<1>{}\2'.format(prefix), twin, count=1)
        newline = "\r\n" if "\r\n" in text else "\n"
        text = text[:m.end("block")] + newline + indent + twin + text[m.end("block"):]
    return text


def exgSectionFromArg(arg):
    """The exgSection argument ("30105", "3012201") as a section ("3.1.5", "3.1.22.1"): one-digit chapter, then
    two-digit levels."""
    return ".".join([arg[0]] + [str(int(arg[i:i + 2])) for i in range(1, len(arg), 2)])


def main(testcasePath, referencesPath, outPath, absolute=False, observed=None):
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
    made, skipped, twins = 0, [], []
    children = list(root)
    for v in children:
        if v.tag.split("}")[-1] != "variation":  # EDGAR's conformance namespace, or XBRL's (the fee testcases)
            continue
        dataFiles = [d for data in v.iter() if data.tag.split("}")[-1] == "data" for d in data
                     if d.text and d.text.strip() and os.path.exists(os.path.join(base, d.text.strip()))]
        instancePaths = [os.path.basename(d.text.strip()) for d in dataFiles if d.tag.split("}")[-1] == "instance"]
        if absolute:  # any data file named relative to the testcase, whatever the testcase namespace
            for d in dataFiles:
                d.text = os.path.join(base, d.text.strip())
        asserts = v.findall(".//{%s}assert" % CONF)  # only EDGAR-namespace testcases carry EFM-section asserts
        if not asserts:
            continue
        a = asserts[0]
        efm = efmSection(a.get("num"))
        concept = a.get("name") or ""
        concept = concept if ":" in concept else "dei:" + concept
        if observed is not None and efm:
            prefix = "EFM.{}.{}.{}".format(*[p if i == 0 else p.zfill(2) for i, p in enumerate(efm.split("."))])
            msgs = [m for ip in instancePaths for m in observed.get(ip, ()) if m[0].startswith(prefix)]
            named = [m for m in msgs if (a.get("name") or "") in m[1]] or msgs
            sections = {exgSectionFromArg(m[2]) for m in named}
        else:
            sections = byEfmConcept.get((efm, concept), set()) if efm else set()
        if len(sections) != 1:
            skipped.append((v.get("id"), a.get("num"), a.get("name"), "no reference" if not sections else "several: " + ", ".join(sorted(sections))))
            continue
        twins.append((v.get("id"), exgPrefix(next(iter(sections)))))
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
    if absolute:
        tree.write(outPath, encoding="utf-8", xml_declaration=True)
        restoreNamespaceDeclarations(testcasePath, outPath)
    else:  # for merging into the suite source: the original text with each twin inserted after its original
        with open(testcasePath, encoding="utf-8", newline="") as fh:  # keep the file's own line endings
            original = fh.read()
        with open(outPath, "w", encoding="utf-8", newline="") as fh:
            fh.write(insertTwinsAsText(original, twins))
    print("{}: {} twins; {} failing variations without a twin".format(os.path.basename(testcasePath), made, len(skipped)))
    for s in skipped:
        print("  no twin:", *s)


if __name__ == "__main__":
    args = sys.argv[1:]
    absolute = "--absolute" in args
    observed = None
    if "--observed" in args:
        i = args.index("--observed")
        import glob
        observed = observedSections(glob.glob(os.path.join(args[i + 1], "*.log.xml")))
        del args[i:i + 2]
    args = [a for a in args if a != "--absolute"]
    if len(args) != 3:
        sys.exit(__doc__)
    main(*args, absolute=absolute, observed=observed)
