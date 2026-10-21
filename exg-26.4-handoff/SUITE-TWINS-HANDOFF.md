# Dual-coded conformance suite: merging EXG twins into EDGAR's conformance repository

This handoff is for an AI coding assistant working inside SEC in EDGAR's conformance-suite repository, and for the
developer working with it. It goes with the 26.4 EXG message-codes pull (`exg-26.4-message-codes`) of
[EXG-26.4-HANDOFF.md](EXG-26.4-HANDOFF.md).

**Revised 2026-10-21.** The twins are now generated for the suite **without** the required-context suite changes,
because the required context is deferred to a later sprint. They are in `suite/codes-suite.zip`. The earlier
`suite/pull2-suite.zip` assumed the required-context suite changes and is kept for reference only.

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

`suite/codes-suite.zip` holds the twins for the suite efm-78-260914 as published:
- `patches/`: the one commit, as `git format-patch` output, for `git am` onto efm-78-260914;
- `files/`: the 29 testcase files that gain twins (2,770 twins in all), at their paths under the suite's `conf/`
  folder, ready to replace the suite's file. In each, the original text is byte-for-byte unchanged, line endings
  included, and the twins are inserted as added lines. Removing the twins gives back the original file exactly. There
  is no index file: the suite's own `conf/testcases.xml` is unchanged;
- `twins.tsv`: per testcase file, the twins made and every failing variation without a twin, with the reason.

They were generated from a default-mode run of `exg-26.4-message-codes` on efm-78-260914, so each twin expects
exactly the EXG section that the plugin's references give its original's message.

A failing variation gets **no twin** when its messages carry no EXG reference: other EFM chapters, hand-coded checks,
and legacy checks without a reviewed EXG counterpart. In EXG mode those keep their EFM codes, so their existing
expectation stands for both modes.

## Merging

**If the conformance repository's suite is efm-78-260914**, apply the patch, or copy the zip's `files/` over the
matching files in `conf/`. Only added lines appear in the diff. (With git's default diff algorithm a few insertions
next to similar text can show as moved lines; `git diff --diff-algorithm=histogram` shows additions only.)

**If it has moved on** (variations added or changed since efm-78-260914), generate the twins from the current suite
instead of copying:

1. With the plugin at `exg-26.4-message-codes`, run the suite in its default (EFM) mode with XML logs, as
   `tools/runSuite.py` does on the fork, or one `arelleCmdLine.py --file <testcase> ... --logFile <name>.log.xml` per
   testcase file. The logs record the `exgSection` argument of every message, which is exactly the EXG section the
   plugin's references give it.
2. Generate:
   ```
   python3 validate/tools/makeExgSuite.py <suite conf/testcases.xml> validate/resources/efm-exg-references.json \
       <out dir> <dir of the run's *.log.xml> --relative
   ```
   `<out dir>` receives only the testcase files that gained twins, as text-preserving copies, and `twins.tsv`.
3. Copy the testcase files over the suite's files.

## Checking

Run the suite with the plugin at `exg-26.4-message-codes`. Two things must hold:
- **every original variation** gives the same status and codes as before (on the fork, as with 26.3);
- **every twin passes.** On the fork, 2,769 of 2,770 do. The exception is `605-40` man `_102gw-exg`, an order effect
  in the suite: in an in-order run its original raises a 3.1.11 message, but run alone, or right after itself, it
  raises a WKSI header-value message that has no EXG reference. It is of the same kind as `605-32 _001ng`, which
  also passes only when run alone.

## Regenerating

Twins depend on `efm-exg-references.json`. When the references change, after a new draft of the guide or a review
ruling, regenerate the twins as in "Merging", step 1 onwards, on the suite as it is, twins included:
`makeExgTwins.py` replaces the twins already in a file rather than adding a second set. Then check again.

## After the required-context pull (later sprint)

The required-context pull comes with its own suite changes (`suite/pull1-suite.zip`): 17 variations its ordering
turns into errors, with corrected copies, and fixes to 605-19, 605-54 and the 3.1.2 periods of report. They were
made on efm-78-260914 without twins. To apply them to a suite that has the 26.4 twins:

1. Remove the twins from the testcase files those changes touch (or from all of them). Removing them gives back each
   original file exactly, so the patches apply cleanly. In Python, with the plugin's tools on the path:
   `makeExgTwins.removeTwinsAsText(text)`.
2. Apply the required-context suite changes.
3. With the plugin at the required-context pull, run the suite in default mode with logs, and regenerate the twins
   as in "Merging". The twin set changes a little, because the required context changes which messages some
   variations raise. On the fork, the result is 2,767 twins: the 2,770 of 26.4 without the ten 605-20 and 605-21
   variations that then raise several cover messages, plus seven twins of the required-context variations.
