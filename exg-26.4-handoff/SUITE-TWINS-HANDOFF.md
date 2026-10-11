# Dual-coded conformance suite: merging EXG twins into EDGAR's conformance repository

This handoff is for an AI coding assistant working inside SEC in EDGAR's conformance-suite repository, and for the
developer working with it. It goes with Pull 2 (EXG message codes) of [EXG-26.4-HANDOFF.md](EXG-26.4-HANDOFF.md).

## What the twins are

The EFM conformance suite expects failures as `<conf:assert num="60520" name="DocumentType" .../>`: an EFM section
and a concept. Arelle reads only a variation's first assert, so the EXG expectation cannot be added beside it.
Instead, each failing variation that can be mapped gets an **EXG twin**, inserted right after it in the same
testcase file:

- id `<id>-exg`, and the name prefixed "EXG mode: ";
- the same data;
- `"messageCodes": "EXG"` added to its `ELOparams`;
- an assert whose `num` is the EXG code prefix, such as `num="EXG.3.01.05"`. Arelle already accepts an EXG `num` and
  matches it as a code prefix, as it does for EFM.

One suite run then checks both modes. When EFM is retired, the original EFM-coded variations can be dropped and the
twins kept.

## What is delivered

`suite/pull2-suite.zip` holds the twins for the suite efm-78-260914 **with Pull 1's suite changes applied** (`suite/pull1-suite.zip`;
conformance working branch `hf-exg-conformance` at `ebbdbca3`) (the required-context
corrections and new variations, delivered with Pull 1), just as Pull 2's code contains Pull 1's. Apply Pull 1's suite
changes first, then these. The zip holds:
- `patches/`: the one commit, as `git format-patch` output, for `git am` onto the suite with Pull 1's changes;
- `files/`: the 30 testcase files that gain twins (2,767 twins in all), at their paths under the suite's `conf/` folder,
  ready to replace the suite's file. In each, the original text is byte-for-byte unchanged, line endings included, and the
  twins are inserted as added lines. Removing the twins gives back the original file exactly;
- `twins.tsv`: per testcase file, the twins made and every failing variation without a twin, with the reason.

A failing variation gets **no twin** when its messages carry no EXG reference: other EFM chapters, hand-coded checks,
and legacy checks without a reviewed EXG counterpart. In EXG mode those keep their EFM codes, so their existing
expectation stands for both modes.

## Merging

**If the conformance repository's suite is efm-78-260914 with Pull 1's suite changes**, copy the zip's files over the matching files in `conf/`.
Only added lines appear in the diff.

**If it has moved on** (variations added or changed since efm-78-260914), generate the twins from the current suite
instead of copying:

1. With the plugin at Pull 2, run the suite in its default (EFM) mode with XML logs, as `tools/runSuite.py` does on
   the fork, or one `arelleCmdLine.py --file <testcase> ... --logFile <name>.log.xml` per testcase file. The logs
   record the `exgSection` argument of every message, which is exactly the EXG section the plugin's references give
   it.
2. Generate:
   ```
   python3 validate/tools/makeExgSuite.py <suite conf/testcases.xml> validate/resources/efm-exg-references.json \
       <out dir> <dir of the run's *.log.xml> --relative
   ```
   `<out dir>` receives only the testcase files that gained twins, as text-preserving copies, and `twins.tsv`.
3. Copy them over the suite's files.

## Checking

Run the suite with the plugin at Pull 2. Two things must hold:
- **every original variation** gives the same status and codes as before;
- **every twin passes.** On the fork, 2,766 of 2,767 do. The exception is `605-40` man `_102gw-exg`, an order effect
  in the suite: in an in-order run its original raises a 3.1.11 message, but run alone, or right after itself, it
  raises a WKSI header-value message that has no EXG reference. It is of the same kind as `605-32 _001ng`, which
  also passes only when run alone.

## Regenerating

Twins depend on `efm-exg-references.json`. When the references change, after a new draft of the guide or a review
ruling, regenerate the twins as in "Merging", step 1 onwards, and check again.
