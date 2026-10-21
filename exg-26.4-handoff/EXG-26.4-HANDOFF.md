# EDGAR XBRL Guide (EXG) work for EDGAR 26.4: EXG message codes now, required context next

This handoff is for an AI coding assistant working inside SEC in the EDGAR plugin repository, and for the developer
working with it. It describes changes prepared on the public fork `hermfischer-xb/EDGAR` and how to bring them onto
SEC's 26.3 branch or the 26.4 work in progress.

**Revised 2026-10-21.** The EDGAR team takes the EXG message codes for 26.4 and defers the required context to a
later sprint. The message-codes pull has therefore been rebuilt so that it no longer contains the required-context
work, and the required-context work has been rebased on top of it for the later sprint. The earlier arrangement, in
which Pull 2 contained Pull 1, is kept on the fork for reference only (see "Earlier branches" below).

## The pulls

| Pull | Branch on the fork | Base | Commits | What it does |
|---|---|---|---:|---|
| **26.4: EXG message codes** | `exg-26.4-message-codes` | 26.3 `4891c4c` | 14 | Messages carry both EFM and EXG references; the `messageCodes` parameter; `efm-exg-references.json`; the tools that build it; the generator for the dual-coded conformance suite. No change to how contexts are selected. |
| **Next sprint: required context** | `exg-next-required-context` | `exg-26.4-message-codes` | 24 | Selects the required context by the EXG ordering, adds the EXG 3.1.2 header check, wires in the instance-type resolver and the parameters it uses. |
| DQC removal | `hf-exg-dqc-removal` | 26.3 `4891c4c` | 1 | Removes the hand-coded Python implementations of DQC.US rules (`b9df825`). Unrelated to EXG; a separate decision. |

Branch heads as handed over:

| Branch | Head | Tree |
|---|---|---|
| `exg-26.4-message-codes` | `c524d67` | `8a755c129657e1e39f7ed16daa23dc9b8b8da4a7` |
| `exg-next-required-context` | `55bd833` | `c1a25bc2d8b7f6d80f78b8af9dd54b1ca55795c2` |
| `hf-exg-dqc-removal` | `b9df825` | |

This handoff, the unit tests and the conformance-suite packages are on the doc-only branch `exg-26.4-handoff`, in the
folder `exg-26.4-handoff/`.

**How the message-codes pull stands alone.**
- Its first commit, `f6e3332`, adds `validate/InstanceTypes.py` and `validate/resources/exg-set-definitions.json`
  (EXG Tables 6-1 to 6-4 and their resolver). The EXG tooling in `validate/tools/` and `validate/resources/exg/build/`
  uses them to evaluate the guide's scope cells. **Nothing at run time calls them in 26.4:** `Filing.py` does not
  import them until the required-context pull wires them in.
- The other commits are the message-code commits of the earlier Pull 2, replayed onto 26.3. Their only conflicts were
  in lists both pulls extend: the parameter documentation and parameter-name sets in `validate/__init__.py`, the
  `.Util` import line in `Filing.py`, and the loaders in `Util.py`. Each keeps 26.3's lines plus `messageCodes` and
  `loadEfmExgReferences`.
- Two tool fixes were added on 2026-10-21 (`55a3d75`, `c524d67`): `makeExgSuite.py --relative` no longer writes an
  empty `testcases.xml` that would replace the suite's index when the output is copied over the suite, and
  `makeExgTwins.py` replaces twins already in a testcase file instead of adding a second set, so the suite can be
  regenerated in place.

**How the two recombine.** `exg-next-required-context` is the 23 required-context commits of the earlier Pull 1
replayed onto `exg-26.4-message-codes`, plus one commit (`55bd833`) that restores the combined order of parameters
and imports. Its tree equals the earlier, fully tested Pull 2 (`7d9b056d`) plus the two tool fixes, and nothing else.

## Bringing the pulls onto SEC's branch

Fetch the fork, then rebase onto SEC's base. For SEC's 26.3 the base is the commit equivalent to `4891c4c`. For the
26.4 work in progress it is that branch's head.

```
git remote add hf https://github.com/hermfischer-xb/EDGAR.git     # once
git fetch hf

# 26.4
git switch -c exg-message-codes hf/exg-26.4-message-codes
git rebase --onto <SEC base> 4891c4c exg-message-codes

# later sprint, on top of the message codes as merged
git switch -c exg-required-context hf/exg-next-required-context
git rebase --onto <SEC branch holding the message codes> hf/exg-26.4-message-codes exg-required-context

# separately, if wanted
git switch -c exg-dqc-removal hf/hf-exg-dqc-removal
git rebase --onto <SEC base> 4891c4c exg-dqc-removal
```

**Line endings.** SEC's GitHub requires CR/LF line endings. Public 26.3 and these branches store their files with LF,
the existing files and the new ones alike. If SEC's copy holds CR/LF, every changed hunk would conflict on line
endings alone. So:
- rebase with `-X renormalize` (or `-X ignore-space-at-eol`);
- then make the result CR/LF throughout, as SEC's repository requires, for example with a `.gitattributes` rule and
  `git add --renormalize .`, before committing.

The one exception is `validate/resources/exg/build/build.sh`: a shell script with CR/LF does not run under a Unix
shell, so keep it LF (`*.sh text eol=lf`) or run it through `dos2unix` before use.

Conflicts to expect are only where SEC's own 26.4 changes touch the same places, most likely:
- `validate/Filing.py`: the message-formatting block in `sevMessage`, and, for the required-context pull, the
  required-context block in `validateFiling`;
- `validate/__init__.py`: the parameter list and its documentation at the head of the file;
- `validate/resources/dei-validations.json`, which the EDGAR team edits each release. The message-codes pull changes
  only the comment that documents `msgSection`; no entry is changed;
- `validate/Consts.py`.

When resolving, keep SEC's changes and add these pulls' changes beside them. If a conflict is not clear, stop and ask
the developer; do not guess.

## Checking the result

1. **Against the reference trees, when the base is 26.3 itself.** After rebasing onto `4891c4c` with no other
   changes, the trees must be exactly those in the table of branch heads above. On another base, compare
   `git diff <SEC base> exg-message-codes` with `git diff 4891c4c hf/exg-26.4-message-codes`: the differences should
   be only SEC's own changes.
2. **The EFM conformance suite** (efm-78-260914 or SEC's current suite), for the message-codes pull:
   - **Default mode (`messageCodes` absent, so `EFM`) is 26.3's behaviour.** On the fork, every variation of
     efm-78-260914 gives the same status and message codes as 26.3.
   - **With the twins** (`suite/codes-suite.zip`, see [SUITE-TWINS-HANDOFF.md](SUITE-TWINS-HANDOFF.md)):
     every original variation gives the same status and codes as without the twins, and 2,769 of the
     2,770 twins pass. The exception is `605-40` man `_102gw-exg`, an order effect in the suite (in an in-order run its
     original raises a 3.1.11 message; run alone it raises a WKSI header-value message with no EXG reference), as on
     the earlier Pull 2.
   - Any difference after rebasing comes from the interaction with SEC's changes and should be looked at.
3. **Unit tests**, in this handoff branch's `exg-26.4-handoff/tests/` folder. Each takes the plugin directory as its
   argument.

   ```
   # 26.4 message codes (and again after the required-context pull)
   python3 exg-26.4-handoff/tests/test_message_references.py <plugin dir>          # needs Arelle's Python, for regex
   python3 exg-26.4-handoff/tests/test_instance_types.py <plugin dir>              # Tables 6-1 to 6-4, scope cells

   # required context (later sprint)
   python3 exg-26.4-handoff/tests/test_select_required_context.py <plugin dir>     # the ordering, steps 1 to 8
   python3 exg-26.4-handoff/tests/test_fee_exhibit_anchor.py <plugin dir>          # fee exhibits: the anchor facts
   python3 exg-26.4-handoff/tests/test_step4_submission_sets.py <plugin dir>       # step 4's submission sets
   python3 exg-26.4-handoff/tests/test_modeldocument_guard.py <plugin dir>         # an instance that did not load
   (cd <Arelle worktree root> && python3 <path>/exg-26.4-handoff/tests/test_document_period_end_date_required.py .)
                                                                                    # step 4b; needs Arelle importable
   ```

   On the fork, the first two pass on `exg-26.4-message-codes`, and all seven pass on `exg-next-required-context`
   (as they did on the earlier Pull 2, whose tree it reproduces). Whether these tests move into the plugin repository
   is the EDGAR team's decision.

## What EXG mode means without the required context

In EXG mode a message carries the EXG section that states the same check, but until the required-context pull lands,
the context the check binds to is still chosen as in 26.3. Where 26.3's choice and the EXG ordering differ, an
EXG-coded message reflects 26.3's choice. On nine months of EDGAR XBRL feeds (December 2025 to August 2026), the
required-context change altered the messages of 9,166 of 140,942 filings (6.5%), mostly by adding EFM 6.5.19 (see
"Required context" below). Those are the filings where EXG-mode results in 26.4 will differ from those after the
required-context pull.

## Earlier branches (reference only)

`exg-26.4-pull1-required-context` (`68541d2`) and `exg-26.4-pull2-message-codes` (`5c290dd`, which contained Pull 1)
stay on the fork as they were handed over on 2026-10-11, with `suite/pull1-suite.zip` and `suite/pull2-suite.zip`.
Use the branches above instead.

## 26.4: EXG message codes (`exg-26.4-message-codes`)

- **Every message from a table-driven check carries its references as arguments:** `efmSection`, and `exgSection`
  where it has an EXG reference. An entry may carry both `efm` and `msgSection`.
- **`messageCodes` chooses which guide forms the code**, as a list in priority order. The default is `EFM`, which
  changes no code. Within EDGAR, pass `messageCodes=EXG` for EXG codes: a check without an EXG reference falls
  back to its EFM code. Listing two guides (`EXG EFM`) also adds `efmCode` and `exgCode` arguments, for comparing
  runs. Going back to EFM codes is a parameter change, not a code change.
- **EXG references for the legacy checks** that carry only an EFM reference are in
  `validate/resources/efm-exg-references.json`: 307 references, reviewed, read at run time.
  - `dei-validations.json` is not edited.
  - No EFM code is created.
  - The file is also meant to be published for filing preparers and consumers of disseminated filings who meet EXG
    codes for the first time.
- **Numeric IDs for EXG codes** use a provisional range, base 100,000,000, encoded from the EXG section left-aligned.
  It is one constant, `exgStart`, in `validate/MessageNumericId.py`, and is documented there for review.
- **Fee-exhibit codes** (`ft.` in `ft-validations.json`) are unchanged.
- **Maintenance** of the EXG resources (a new Word draft of the guide, a requirements change, an urgent fix) is
  described in `validate/resources/exg/handoffs/README.md`. The build scripts are in `validate/resources/exg/build/`
  and the analysis tools in `validate/tools/`.
- **The dual-coded conformance suite** is a separate handoff: [SUITE-TWINS-HANDOFF.md](SUITE-TWINS-HANDOFF.md), with
  `suite/codes-suite.zip`.

## Next sprint: required context (`exg-next-required-context`)

**Reading the history.** Some commits are kept because they record how the series developed, though later ones
supersede them:
- `7681ebc` "WIP: select the required context…" is superseded by `ee8bc3c`;
- `65aae0c` "Proposed: step 4d takes the latest end date not after the filing date" is superseded by `7627c7a`;
- `37f9441`, `9e354bb` and `b71cbd2` add a log-only "cover-anchored" comparison selection (parameter
  `requiredContextShadow`) for batch analysis. It affects no validation.

Squash these if the team prefers a shorter history; the reference tree is the same either way. On
`exg-next-required-context` they carry new commit ids, followed by `55bd833`.

**Its conformance-suite changes** are delivered as `suite/pull1-suite.zip` on this handoff branch, with its own README:
17 variations the ordering turns into errors are corrected, with corrected copies, and one 605-19 variation is fixed.
In the later sprint they go onto a suite that already has the 26.4 twins: see SUITE-TWINS-HANDOFF.md, "After the
required-context pull".

### What changes in behaviour

**1. The required context is selected by the ordering the EXG author gave.** 26.3 took the context holding
`dei:DocumentType`, or failing that the first duration with no segment. Pull 1 orders the contexts of an
instance and takes the first; code and docstrings are in `validate/RequiredContext.py`.

1. The entity identifier matches a CIK of the submission header, failing that it is all zeroes.
2. The context has no custom axis. A custom member of a standard axis does not disqualify it.
3. Contexts ending more than one business day after the filing date are set aside, when a filing date is known
   and some context survives. Then the fewest standard dimensions.
4. Only for submissions in sets 6K, 8K, AF, EBP, HF, OA, PX, QF, RF, SE, TF and TO (EXG Table 6-1):
   - (a) durations of 28 to 371 days;
   - (b) the one holding `dei:DocumentPeriodEndDate`, if exactly one does and the submission type requires
     that fact;
   - (c) the longest in whole quarters;
   - (d) the latest end date;
   - (e) order of appearance.
5. The latest-ending one-day duration.
6. The latest-ending duration under 28 days.
7. The latest-ending duration over 371 days.
8. Order of appearance.

- **Fee exhibits** (`EX-FILING FEES`) take the context of `ffd:FeeExhibitTp`, failing that of
  `dei:EntityCentralIndexKey`, failing that of `dei:EntityRegistrantName`, and the ordering otherwise. The
  step-3 bound does not apply to an anchor's context; the header check below reports such a context instead.
- **Business days** are the federal holidays of 5 U.S.C. 6103, with Saturday and Sunday observance, plus the
  EDGAR closures observed in the feeds (`EDGAR_OBSERVED_CLOSURES`: 2025-01-09, 2025-12-24, 2025-12-26). That
  list needs extending as further closures occur.
- **The EXG author's rulings are data**, in `validate/resources/required-context.json`: the step-4 submission
  sets, and the scope of the header check. A further ruling is an edit there.

**2. The EXG 3.1.2 header check (EFM 6.5.19, error) is new.** It is reported when no context that could be the
required context (steps 1 and 2) is a duration ending on the header's period of report, or within
[min(5 business days, 6 calendar days) before, max(1 business day, 4 calendar days) after] the filing date.

- It is made only when the header gives one of those dates.
- Its scope is the guide's own Incl cell, "i:ALL": every instance with an EXG instance type.
- 26.3 never compared header dates with contexts.
- A second 6.5.19 message, "A required context was not found", is reported when no context passes steps 1 and
  2, and states which step failed.

**3. Messages that bind to the required context follow the new selection.** Where the selected context differs
from the one holding the cover facts, the cover facts can be reported missing.

**4. Measured on nine months of EDGAR XBRL feeds**, December 2025 to August 2026, 140,942 filings validated by
both 26.3 and these changes:
- EFM 6.5.19 is added to 8,732 filings by the header check and to 63 by "not found". Most are:
  - DEF 14A 3,165 of 3,556: the header period of report is the meeting date;
  - PRE 14A 520;
  - 485BPOS 1,293 and 497 1,162: no period of report, and the filing comes months after the period;
  - Form SD 78 of 78.
- Cover facts are reported missing on about 1,180 filings, mostly registration statements whose cover facts sit
  in financial-statement periods while step 5 selects a one-day context.

These consequences have been reported to the EXG author. The decision for 26.4 is to ship the check as the guide
writes it and let the filer community assess it during the preview period.

**5. EXG instance types are resolved for every instance**, in `validate/InstanceTypes.py` (already present, unused,
since the 26.4 message-codes pull; this pull calls it).
- **The tables are data:** `validate/resources/exg-set-definitions.json` holds EXG 1.1 "Set Definitions",
  Tables 6-1 to 6-4, generated from the guide's Word source. Do not edit it by hand; regenerate it for each
  edition of the guide.
- **Two uses so far:** step 4's submission sets, and the header check's scope. No other rule uses them yet.
- **`scopeApplies`** evaluates EXG Incl/Excl cells on an instance.

**6. Robustness.** A filing whose instance did not load is skipped, rather than raising an exception in the
plugin's testcase/RSS hooks.

### Parameters

| parameter | meaning | when absent |
|---|---|---|
| `filingDate` | the filing date EDGAR assigns (mm-dd-yyyy or yyyy-mm-dd). It bounds the selection (step 3) and the header check | no bound; the header check uses the period of report only |
| `periodOfReport` | the header period of report (mm-dd-yyyy), for the header check | the header check uses the filing date only; with neither date it is not made |
| `entitySets` | EXG Table 6-3 entity sets of the registrant, from the registration database: a JSON list, or one blank-separated string from formula or GUI parameters, as for the `seriesIds` parameters | determined from the submission (see below) |
| `submissionType`, `attachmentDocumentType` | as in 26.3 | inferred as in 26.3: a fee exhibit (ffd taxonomy) is `EX-FILING FEES` with the submission type from `ffd:SubmissnTp`; otherwise both come from `dei:DocumentType` |
| `invCompanyType` | as in 26.3; it also names the form inside a 485BPOS or 497 (Table 6-2's `#N1` ... `#N6`) | `dei:EntityInvCompanyType` |
| `fileNumber` | as in 26.3; an `814-` number identifies a business development company for entity sets | `dei:EntityFileNumber` |
| `logRequiredContext`, `logInstanceTypes` | true: one info record per instance (`EDGAR.requiredContext`, `EDGAR.instanceTypes`) giving the selection and its deciding step, or the instance types and how each was decided | no record |
| `rssItemParameters` | true, when validating an EDGAR RSS feed: take `submissionType`, `cik`, `periodOfReport` (not 1969-12-31) and `filingDate` from each feed item | not taken |
| `requiredContextShadow` | "cover": log a cover-anchored selection beside the required context, for batch comparison only | not logged |

**Entity sets when `entitySets` is absent** are determined from the submission alone, so that a filer's
pre-submission validation and downstream users get the closest answer available.
- The rules choose among the rows Table 6-4 gives for each submission set:
  - 6-K: FPI.
  - 10-K or 10-Q under an `814-` file number: BDC.
  - 20-F: FPI; 40-F: CA.
  - N-CSR: CEF or OEF by investment company type or use of the cef taxonomy.
  - F- forms: FPI; S-11: RT; S-6: UIT; 20FR: FPI; 40FR: CA.
  - Form 1: SRO.
  - the form inside an RD submission: OEF, CEF, V3, V4 or V6.
  - SBSEF submissions: SBSEF.
  - SPAC by an Exhibit 98 or spac facts.
  - US otherwise.
- With `entitySets` given, the parameter decides. The determined sets are still computed, and
  `logInstanceTypes` reports a disagreement in any entity set that a Table 6-4 row of the submission's sets names.

**Readings that are ours, pending the EXG author:**
- An instance that is itself an exhibit named in Table 6-4 (fee exhibit, EX-98, EX-2.01, the K and L SDR
  exhibits, EX-99.4R HISTORIC, the SBSEF exhibits) takes only that row's instance types. Every other instance
  takes the rows that name no exhibit.
- EXG's "Exhibit Type" is matched against `attachmentDocumentType` (an EDGAR document type), not against the
  `exhibitType` parameter.


## Not in these pulls

- `validate/ContextClasses.py`, EXG's context classes for the future EXG-shaped rules file, is on the fork's
  `hf-exg-tooling` branch. Nothing uses it yet.
- The EXG-shaped rules file that would replace `dei-validations.json`. It is planned after 26.4.
