"""Write the plugin resource efm-exg-references.json from the reviewed candidates (validate/tools/references.py's candidates.tsv, kept here as
references-candidates.tsv).

The resource maps a legacy check, identified by its EFM section, validation code, axis key and concept, to the
EDGAR XBRL Guide section whose code it carries in EXG mode.  Only reviewed references go in: "ruling" (rulings
made in review, ../handoffs/mapping-rulings.md), "code" (the row's EFM cell code is the legacy validation code) and "section"
(confirmed by a sample review of review-first.md).  Duplicate keys must agree, or the build stops.

Usage: python3 buildReferences.py <candidates.tsv> <edition> <review note> <out efm-exg-references.json>
"""
import csv, json, sys

REVIEWED = ("ruling", "code", "section")


def main(candidatesPath, edition, reviewNote, outPath):
    refs = {}
    with open(candidatesPath, newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            if r["tier"] not in REVIEWED:
                continue
            key = (r["efm"], r["validation"], r["axis"], r["concept"])
            rows = [x.split(" c=")[0] for x in r["candidates"].split(" | ") if x]
            if key in refs:
                if refs[key]["exg"] != r["exgSection"]:
                    sys.exit("conflicting references for {}: {} and {}".format(key, refs[key]["exg"], r["exgSection"]))
                refs[key]["rows"] = sorted(set(refs[key]["rows"]) | set(rows))
                continue
            refs[key] = {"efm": r["efm"], "validation": r["validation"], "axis": r["axis"], "concept": r["concept"],
                         "exg": r["exgSection"], "basis": r["tier"], "rows": rows}
    out = {
        "comment": [
            "EDGAR XBRL Guide (EXG) references for legacy checks (dei-validations.json entries) that carry only an EDGAR",
            "Filer Manual (EFM) reference. A check is identified by its EFM section, validation code, axis key and the",
            "concept its message names; exg is the EXG section whose code the message carries when the messageCodes",
            "parameter lists EXG first, and which every message from such a check gives as its exgSection argument.",
            "rows are the EXG section 3 rows the reference rests on (section#row). basis: ruling (decided in review),",
            "code (the row's EFM cell code is the validation code), section (concept and EFM section agree; confirmed",
            "by sample review). Generated; do not edit by hand. Published for filing preparers and consumers of",
            "disseminated filings who meet EXG codes for the first time."],
        "edition": edition,
        "review": reviewNote,
        "references": sorted(refs.values(), key=lambda r: ([int(x) for x in r["exg"].split(".")], r["efm"],
                                                          r["validation"], r["axis"], r["concept"])),
    }
    # one reference per line, so the file reads as a table and diffs line by line
    body = json.dumps({k: v for k, v in out.items() if k != "references"}, indent=1, ensure_ascii=False)[:-2]
    lines = [json.dumps(r, ensure_ascii=False) for r in out["references"]]
    with open(outPath, "w", encoding="utf-8") as fh:
        fh.write(body + ',\n "references": [\n  ' + ",\n  ".join(lines) + "\n ]\n}\n")
    print(len(refs), "references written to", outPath)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
