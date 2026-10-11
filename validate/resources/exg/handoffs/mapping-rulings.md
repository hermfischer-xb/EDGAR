# Mapping the legacy checks to EXG rows: rules and rulings

This file records how the plugin's legacy checks (`dei-validations.json`) are matched to EDGAR XBRL Guide section 3
rows, for `efm-exg-references.json` and the conformance suite's EXG variations. Every ambiguity is
settled in review; this is the record of the rulings and of the evidence each one rests on.

## How a legacy check is matched

- **Concept and EFM section first.** A legacy check is matched by its concept and its EFM section. Where those
  leave several sections, the legacy entry's context decides: the legacy file splits contexts by EFM section exactly
  as EXG splits them by its `c` column.

  | Legacy | EXG |
  |---|---|
  | 6.5.48, no axis: principal office, in the required context | 3.1.22, `c = r` |
  | 6.5.51, axis `a`: business contact (BusinessContactMember or UsAgentContactMember) | 3.2.1, `c = bc` (BusinessContactMember only) |
  | 6.5.53, axis `f`: former address | 3.2.2, `c = fa` |
  | 6.5.57, `oef:class`, all on N-CSR forms | 3.2.6, `c = cc` |

  A context class is not inferred from the absence of an axis: there can be many contexts without dimensions,
  and the required context is the one of them that meets the required-context rules (review, 2026-10-10).
- **The subject of a check, not a condition** (review, 2026-10-10). Where a concept appears in several sections,
  the section where it is the checked fact decides, not one where it only conditions another fact. For example,
  EntityAddressAddressLine1 goes to 3.1.22.1, not 3.1.22.2.
- **3.1.1 creates no checks** (review, 2026-10-10). It is the notation section: its tables follow "an example is
  shown below" and are the pattern for the sections after it, so its rows are never linked.
- **Where EXG states a check more finely or more than once, the plugin follows EXG as written for now**, and the
  question is reported to the EXG author (review, 2026-10-10). A future Word draft that changes it is applied like any
  other guide change.

## Rulings

| Legacy | EXG | Ruling and evidence |
|---|---|---|
| 6.5.46 `security-axis` (Security12bTitle, Security12gTitle) | 3.2.4.1 rows 1-2 | The legacy check is "one non-ADR fact with no dimensions, or every fact in an axis context, not both". 3.2.4.1 rows 1 and 2 are "present in at most one of the cases 1-3": case 1 is no axis, cases 2 and 3 are at least two members on StatementClassOfStockAxis or ClassesOfShareCapitalAxis. A single security in a one-member axis context is in no case, and only the legacy check flags it (reported to the EXG author) |
| 6.5.46 `ot1` (12b or 12g, not both) | 3.2.4.1 row 3 | "At most one {1} or {2} fact is present" |
| 6.5.46 `te` (SecurityExchangeName depends on Security12bTitle) | 3.2.4.3 | |
| 6.5.46 `t1` (TradingSymbol or NoTradingSymbolFlag) | 3.2.4.4 | |
| (none) | 3.2.4.2 (EntityListingsExchangeAxis) | A new EXG check with no legacy counterpart |
| 6.5.55 N-2 registration flags and file numbers (legacy 360-365) | 3.1.24.1 | EXG splits N-2 by concept, not by original versus amendment. Both 3.1.24.1 and 3.1.24.2 are `i: RD.CEF` and start "If the submission type is N-2, then ... absent". RD.CEF reaches the forms the legacy `@N-2-a` does (the N-2 family, and 486*, POS 8C, POS AMI carrying an N-2) |
| 6.5.55 pre- and post-effective amendments and their numbers (legacy 366-369, 377-378) | 3.1.24.2 | as above |
| 6.5.48 `ol1`/`ol2` (address lines 2 and 3, principal office) | 3.1.22.2 rows 1, 4 | |
| 6.5.51 `ol1`/`ol2` (business contact) | 3.1.22.2 rows 1, 4 (`c = a`) | 3.2.1.2 has no such rows, so the all-contexts rows apply. Same code as the principal-office case |
| 6.5.51 `r`/`o` LocalPhoneNumber (business contact; legacy 323, 324, 326, 327, 330, 331, 333) | 3.2.1.4 | EXG checks it in 3.2.1.1 row 5 and 3.2.1.4 row 4, both `i: AF.CA`. 3.2.1.4 "Phone" was chosen because the number is no use without the area code checked with it there (review, 2026-10-10). Suggested fix for the EXG author. Legacy 322 (`o3`) stays on 3.2.1.1 row 4, its own check |
| 3.2.6 scope | `s: HF, i: AF.OEF` | Read as AF.OEF in place of AF.CEF (review, 2026-10-10): closed-end N-CSRs carry no oef facts, while open-end N-CSRs do (a census of December 2025 to August 2026 filings: 2,115 open-end N-CSRs carry the oef facts, 249 closed-end ones use the cef taxonomy and carry none). It can change with a future guide. Suggested fix for the EXG author |
| 6.5.53 `ol1`/`ol2` (former address) | 3.2.2.1 rows 4, 6, and also 3.1.22.2 rows 1, 4 | Implemented twice, as EXG states it; reported to the EXG author (review, 2026-10-10) |
