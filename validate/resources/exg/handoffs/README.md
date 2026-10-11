# EXG resources: how they are built and maintained

This folder lives with the code so that a maintainer, or an AI assistant working for one, can pick up the EDGAR
XBRL Guide (EXG) work from here. It covers the resources generated from the guide, the tools that build and check
them, and the decisions they rest on.

## The pieces

| File | What it is | Built by |
|---|---|---|
| `validate/resources/exg-set-definitions.json` | EXG 1.1 "Set Definitions", Tables 6-1 to 6-4: submission sets, suffixes, entity sets, instance types | `build/extractSets.py`, from the guide's Word source |
| `validate/InstanceTypes.py` | Resolves an instance's submission sets, entity sets and instance types. Evaluates a rule's Incl/Excl scope cells (`scopeApplies`) | hand-written; no Arelle imports, so it can be tested alone |
| `validate/resources/efm-exg-references.json` | Maps a legacy check (`dei-validations.json` entry: EFM section, validation code, axis key, concept) to the EXG section whose code it carries. Read at run time (`MessageReferences.inferredMsgSection`), and published for filing preparers and consumers of disseminated filings | `build/buildReferences.py`, from the reviewed `build/references-candidates.tsv` |
| `build/extract.py` | The guide's section 3 validation and concept tables to JSON (`guide.json`) | |
| `tools/crosswalk.py`, `tools/weight.py` | Compare the legacy rules' scopes with EXG's by situation, and weight the differences by a corpus of filings | |
| `tools/references.py`, `tools/review.py` | Candidate EXG references for the legacy checks, and a risk-ranked short list for review | |
| `tools/makeExgTwins.py` | Adds EXG-mode twins to a conformance-suite testcase file | |
| `mapping-rulings.md` | The rules and rulings the references rest on | |

## Rebuilding after a new Word draft or edition of the guide

```
sh validate/resources/exg/build/build.sh <guide.docx> "<edition>" "<review note>" [work dir]
```

1. This regenerates `exg-set-definitions.json`. Where the guide's text cannot be used as written, `extractSets.py`
   applies a listed correction and records it in the file's `corrections`. A correction that the guide has since
   fixed reports itself unused.
2. It extracts the tables, reruns the crosswalk, and writes fresh reference candidates to the work directory.
3. **The candidates are not used until reviewed.** Compare `work/refs/candidates.tsv` with
   `build/references-candidates.tsv`:
   - a pair whose section changed, or that is newly ambiguous, needs a decision;
   - `tools/review.py` ranks the settled pairs by risk for a sample review;
   - record each new ruling in `tools/references.py` (`RULINGS`) and in `mapping-rulings.md`.

   Then copy the reviewed candidates over `build/references-candidates.tsv` and run `build.sh` again.
4. Run the EFM conformance suite: legacy-mode results must not change.

The guide does not give its rules stable identifiers: sections and rows renumber between editions. A message's EXG
code therefore follows the edition's section number. Tracking rules across editions is planned work: a content
fingerprint, and a registry of numeric IDs that are never reused.

## Message codes

- The `messageCodes` parameter lists guides in priority order. The default is `EFM`.
  - `EFM`: a check keeps its EFM code where it has one.
  - `EXG`: a check takes its EXG code where it has an EXG reference, and falls back to EFM otherwise.
  - Listing two guides (`EXG EFM`) also gives every message `efmCode` and `exgCode` arguments, for comparing runs.
- An entry's own `msgSection` is its EXG reference. An entry with only an EFM reference takes the one
  `efm-exg-references.json` gives its check, when every concept the message names maps to the same section.
- Messages with an EXG reference carry the `exgSection` argument in every mode.
- `ft-validations.json` (fee exhibits) keeps its `ft.` codes, which are independent of both EFM and EXG section
  numbers.

## Readings of the guide

These readings are ours, not the guide's. They are implemented in `InstanceTypes.py` and stated there.

- **Exhibit instances.** An instance that is itself an exhibit named by a matching Table 6-4 row (the fee exhibit,
  EX-98, EX-2.01, the K and L SDR exhibits, EX-99.4R HISTORIC, the SBSEF exhibits) has only those rows' instance
  types. For `s:` cells, it is in a submission set only where that set holds nothing but exhibits (FE, SE, TO).
- **FE holds only fee exhibits.** An S-1's primary document is not "in FE", although Table 6-1 lists S-1 under FE.
- **ALL**, under `s:` or `i:`, is every instance that is in a submission set or has an instance type, fee exhibits
  included. The guide excludes the fee exhibit by name where a section-3 check should not apply to it.
- **The guide's slips in scope cells** are read as evidently meant, and reported by `parseScopeCell`: a submission
  set under `i:` or an instance type under `s:`, a missing comma, "All".
- **A document type standing in for the submission type** when an exhibit is previewed without parameters:
  `K SDR` and `L SDR` resolve as SDR, and `2.01 SD` as SD.

## Entity sets

Inside EDGAR, the caller passes the registrant's entity sets (Table 6-3 codes) as the `entitySets` parameter. Elsewhere,
`InstanceTypes.determineEntitySets` determines them from the submission, which is our proposal, not EXG text:
- FPI from a 6-K, 20-F or an F- form;
- CA from a 40-F or 40FR;
- BDC from an `814-` file number;
- CEF or OEF from the investment company type, or from use of the cef taxonomy;
- SPAC from an Exhibit 98, or from spac facts;
- US by default.

When both are available, the parameter decides, and a disagreement is logged (`logInstanceTypes`).

## Not done yet

The plan to an EXG-shaped rules file, `exg-validations.json`, which would retire `dei-validations.json`:
- context classes for the guide's `c` column;
- rule identity;
- an engine extending the `ft-validations.json` dialect with scope cells, context classes, parameters and absence
  rows;
- a generator from the guide, with listed corrections and a hand-kept overlay;
- Python handlers for rows that do not compile;
- a dual-mode conformance suite;
- maintenance templates for each kind of change: a new Word draft, a requirements document from the rule makers,
  an urgent fix by the EDGAR team.
