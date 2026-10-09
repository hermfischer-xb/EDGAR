"""
See COPYRIGHT.md for copyright information.

The EDGAR required context: selecting it by the ordering the EDGAR XBRL Guide (EXG) author gave on 2026-09-14
and has revised since, and the business-day arithmetic of the filing-date bound.  The functions take plain
values rather than the validation state, so that they can be tested without loading a filing.
"""
import datetime
from arelle import XmlUtil


def edgarDateParamValue(dateParam):
    """Normalize an EDGAR date parameter to an ISO yyyy-mm-dd string, or None.

    EDGAR supplies dates such as periodOfReport and filingDate as mm-dd-yyyy, whereas a
    command line, GUI formula parameter or web interface caller more naturally writes ISO
    yyyy-mm-dd.  The two forms are distinguished by which group has four digits, so both are
    accepted.  Any other value is returned as-is for the caller's comparison to simply fail.
    """
    if not dateParam:
        return None
    parts = str(dateParam).strip().split("-")
    if len(parts) == 3 and len(parts[2]) == 4:  # mm-dd-yyyy
        return "{2}-{0}-{1}".format(*parts)
    return str(dateParam).strip()  # already yyyy-mm-dd, or unrecognized


def requiredContextEligibleContexts(contexts, headerCiks, isStandardNamespace):
    """Steps 1 and 2 of the EDGAR required context ordering (see selectRequiredContext).

      contexts             ModelContext objects in order of appearance
      headerCiks           submission header CIKs; when empty (not known) step 1 is skipped
      isStandardNamespace  function of a namespace URI, true for a standard taxonomy namespace

    Returns (eligibleContexts, None), or ([], "1a") or ([], "2a") when no context is eligible.
    """
    def identifier(cntx):
        entityIdentifier = cntx.entityIdentifier
        return ((entityIdentifier[1] if entityIdentifier else None) or "").strip()
    eligible = list(contexts)
    # step 1: entity identifier matching a submission header CIK, else all zeroes
    if headerCiks:
        eligible = ([c for c in eligible if identifier(c) in headerCiks] or
                    [c for c in eligible if identifier(c) and not identifier(c).strip("0")])
        if not eligible:
            return [], "1a"
    # step 2: a context with any custom axis is ineligible
    eligible = [c for c in eligible
                if all(isStandardNamespace(getattr(dimQname, "namespaceURI", None)) for dimQname in c.qnameDims)]
    if not eligible:
        return [], "2a"
    return eligible, None


def usFederalHolidaysObserved(year):
    """The US federal holidays of `year`, on the dates EDGAR observes them.

    EDGAR assigns no filing date to a weekend or a federal holiday, so business-day arithmetic on a filing
    date needs the observed dates: a holiday falling on a Saturday is observed on the Friday before and one
    falling on a Sunday on the Monday after (5 U.S.C. 6103).  Juneteenth became a holiday in 2021.
    """
    def nthWeekday(month, weekday, n):  # the n-th such weekday of the month, 1-based
        first = datetime.date(year, month, 1)
        return first + datetime.timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))

    def lastWeekday(month, weekday):
        last = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        return last - datetime.timedelta(days=(last.weekday() - weekday) % 7)

    holidays = [datetime.date(year, 1, 1), nthWeekday(1, 0, 3), nthWeekday(2, 0, 3), lastWeekday(5, 0),
                datetime.date(year, 7, 4), nthWeekday(9, 0, 1), nthWeekday(10, 0, 2),
                datetime.date(year, 11, 11), nthWeekday(11, 3, 4), datetime.date(year, 12, 25)]
    if year >= 2021:
        holidays.append(datetime.date(year, 6, 19))
    observed = set()
    for holiday in holidays:
        if holiday.weekday() == 5:    # Saturday, observed on the Friday before
            holiday -= datetime.timedelta(days=1)
        elif holiday.weekday() == 6:  # Sunday, observed on the Monday after
            holiday += datetime.timedelta(days=1)
        observed.add(holiday)
    return observed


# Weekdays on which EDGAR assigned no filing date although they are not federal holidays, observed in the
# EDGAR XBRL feeds for 2025-01 through 2026-08.  Federal offices closed by executive order on each: 9 January
# 2025 was the national day of mourning for President Carter, and 24 and 26 December 2025 adjoined Christmas.
# Such closures cannot be derived from any rule, so this list is evidence and will need extending; a date
# wrongly present only widens a tolerance window, which is the safe direction.
EDGAR_OBSERVED_CLOSURES = frozenset({
    datetime.date(2025, 1, 9), datetime.date(2025, 12, 24), datetime.date(2025, 12, 26)})


def businessDayOffset(date, offset):
    """`date` shifted by `offset` business days, skipping weekends, federal holidays and observed closures."""
    step = 1 if offset >= 0 else -1
    holidays = (usFederalHolidaysObserved(date.year) | usFederalHolidaysObserved(date.year + step)
                | EDGAR_OBSERVED_CLOSURES)
    remaining = abs(offset)
    while remaining > 0:
        date += datetime.timedelta(days=step)
        if date.weekday() < 5 and date not in holidays:
            remaining -= 1
    return date


def contextLastDay(cntx):
    """The last day of a context's period, as a date; a date-only end date is held as the following midnight."""
    end = cntx.endDatetime
    if getattr(end, "dateOnly", (end.hour, end.minute, end.second, end.microsecond) == (0, 0, 0, 0)):
        end = end - datetime.timedelta(days=1)
    return end.date()


# dei-validations.json validation codes under which a fact is required, or optional, for a submission type
FACT_REQUIRED_VALIDATIONS = frozenset({"r", "de", "de5pm"})
FACT_OPTIONAL_VALIDATIONS = frozenset({"o"})


def documentPeriodEndDateRequired(sevs, localName, submissionType, deiDocumentType, attachmentDocumentType):
    """Whether dei:DocumentPeriodEndDate is required for this submission, according to dei-validations.json.

    False only when an entry applying to the submission makes the fact optional and none makes it required;
    True otherwise, including when no entry applies, so that step 4b keeps its effect wherever the table is silent.

    An entry applies by the same test as the sub-type-element-validations loop in Filing.py: its compiled
    sub-types include the submission type, or the submission type with the dei:DocumentType as "\u00a7" suffix
    (reversed by "!not!"), or its sub-types are "all" or "n/a", subject to its sub-types pattern and document
    types.  That test is repeated here rather than shared, so as not to restructure the loop; a change to one
    should be made to the other.

      sevs                    deiValidations["sub-type-element-validations"]
      localName               local name of the DocumentPeriodEndDate element (disclosure system setting)
      submissionType          submission type, with any "\u00a7" suffix, as the loop in Filing.py uses it
      deiDocumentType         value of dei:DocumentType, or None
      attachmentDocumentType  attachment document type, or None
    """
    formsToMatch = {submissionType, "{}\u00a7{}".format(submissionType, deiDocumentType)}
    required = optional = False
    for sev in sevs:
        validation = sev.get("validation")
        if validation not in FACT_REQUIRED_VALIDATIONS and validation not in FACT_OPTIONAL_VALIDATIONS:
            continue
        names = sev.get("xbrl-names", ())
        if isinstance(names, str):
            names = (names,)
        if not any(name and name.rpartition(":")[2] == localName for name in names):
            continue
        subTypes = sev.get("subTypeSet", frozenset())
        subTypesPattern = sev.get("subTypesPattern")
        docTypes = sev.get("docTypes")
        notApplicable = (subTypes not in ({"all"}, {"n/a"})
                         and (formsToMatch.isdisjoint(subTypes) ^ ("!not!" in subTypes))
                         and (not subTypesPattern or not subTypesPattern.match(submissionType))
                         and (not docTypes or ((attachmentDocumentType is not None and
                                                any(attachmentDocumentType.startswith(dt) for dt in docTypes))
                                               ^ ("!not!" in docTypes))))
        if not notApplicable:
            required |= validation in FACT_REQUIRED_VALIDATIONS
            optional |= validation in FACT_OPTIONAL_VALIDATIONS
    return not (optional and not required)


def selectRequiredContext(eligibleContexts, durationWindow, documentPeriodEndDateContexts, filingDate=None,
                          documentPeriodEndDateRequired=True):
    """Select the required context by the ordering of contexts that defines it for EDGAR.

    EDGAR XBRL Guide (EXG) 3.1 states conditions for the required context.  On 2026-09-14 the EXG author
    (W. Hamscher) gave a normative total ordering of the contexts of an instance that selects it, not yet in
    the published guide, and revised step 4 the same day (longest rather than shortest duration, QF added,
    step 4b added).  On 2026-09-16, after this selection was measured against three months of filings, he replaced
    4d with the latest end date and moved order of appearance to 4e.  Step numbers are his.

      1. An entity identifier matching a submission header CIK, failing that one of all zeroes.  If neither
         exists there is no required context (EFM 6.5.19).
      2. No custom axis: "The presence of a custom AXIS makes the context ineligible to be a required
         context."  A custom member of a standard axis does not.  If every context has a custom axis there
         is no required context.
      3. The fewest standard dimensions, typically but not necessarily none.
      4. If the submission is in set 6K, 8K, AF, EBP, HF, OA, PX, QF, RF, SE, TF or TO (EXG Table 6-1):
         a. durations of 28 to 371 days; if there are none, continue at step 5
         b. if exactly one of them holds a dei:DocumentPeriodEndDate fact, that one, where the submission type
            requires the fact
         c. otherwise the longest, with durations rounded to the nearest multiple of 91 days (so 364 and 371
            days are both four quarters, and 46, 90 and 98 days are each one)
         d. otherwise the latest end date among them
         e. then order of appearance, as in step 8, which the EXG author calls the desperation fallback
         FAST and AM are not listed because each of their submission types is also in a listed set.  The
         period of report is not used: the header period becomes non-normative in 2027, registration
         submissions have none, and dei:DocumentPeriodEndDate's value is itself a fact of the required
         context.  Step 4b is applied among the durations of step 4a.
         Step 4b is skipped where dei-validations.json makes dei:DocumentPeriodEndDate optional for the submission
         type (the proxies, POS AM, POS EX and the 11-K family), following the EXG author's principle of
         2026-09-18 that a fact whose presence or absence causes no message must not identify the required
         context.  Over twenty months of the EDGAR XBRL feeds (2025-01 to 2026-08), 196 filings of those types
         were decided at 4b, and all 196 select the same context without it.
      5. The latest end date among durations of exactly 24 hours.
      6. The latest end date among durations of less than 28 days.
      7. The latest end date among durations of more than 371 days.
      8. Order of appearance in the instance.

    Before step 3, contexts ending more than one business day after the filing date are excluded, when a
    filing date is known and any context survives the exclusion.  This is the EXG author's bound of
    2026-09-18 ("the end date of the required context should never be significantly later than the filing
    date... such contexts could be excluded from consideration at an earlier step"), which he put at a closed
    interval of [-5, +1] business days where business days can be determined, as they can here.  Without it a
    forward-looking plan or award year, or a mistyped future context, wins step 4d: nine proxies over March,
    May and August 2026, one of them tagging 2035.

    The required context is a duration, so step 3 and those after it apply to duration contexts.  Instants are
    never selected: the EXG author dropped step 9, the instant at the required context's end date, on
    2026-09-18, the public float that might have used it now being covered by a rule of its own.

    Arguments are plain values rather than the validation state, so that the selection can be unit tested
    against constructed context objects instead of by loading a filing:
      eligibleContexts               contexts remaining after steps 1 and 2 (requiredContextEligibleContexts),
                                     in order of appearance
      durationWindow                 whether step 4 applies: the submission is in one of the EXG submission sets
                                     the EXG author named for it (resources/required-context.json), decided by
                                     the caller from the submission's sets (InstanceTypes, EXG Table 6-1)
      documentPeriodEndDateContexts  contexts holding a dei:DocumentPeriodEndDate fact, for step 4b
      filingDate                     the submission's filing date as a datetime.date, or None; contexts
                                     ending more than one business day after it are excluded
      documentPeriodEndDateRequired  False where the submission type makes dei:DocumentPeriodEndDate optional
                                     (documentPeriodEndDateRequired()), which skips step 4b

    Returns (requiredContext, step), where step is the step that decided the required context ("4b", "4c",
    "4d", "4e", "5", "6", "7" or "8"), or (None, None) when no eligible context is a duration.  Step 4c decides when one duration is longest, 4d when several are equally long and
    one of them ends latest, and 4e when equally long durations also end on the same date.
    """
    if filingDate is not None:  # the EXG author's bound, applied before the ordering rather than within it
        latestAllowed = businessDayOffset(filingDate, 1)
        withinBound = [c for c in eligibleContexts
                       if c.endDatetime is None or contextLastDay(c) <= latestAllowed]
        if withinBound:  # a filing whose every context ends later keeps them, to select rather than fail
            eligibleContexts = withinBound
    durations = [c for c in eligibleContexts
                 if c.isStartEndPeriod and c.startDatetime is not None and c.endDatetime is not None]
    if not durations:
        return None, None
    # step 3: fewest standard dimensions
    fewest = min(len(c.qnameDims) for c in durations)
    durations = [c for c in durations if len(c.qnameDims) == fewest]

    def days(cntx):  # endDatetime is the day after a date-only end date, so this counts days inclusively
        return (cntx.endDatetime - cntx.startDatetime).days
    chosen = step = None
    # step 4
    if durationWindow:
        window = [c for c in durations if 28 <= days(c) <= 371]  # 4a
        if window:
            withDocumentPeriodEndDate = [c for c in window if c in documentPeriodEndDateContexts]
            if documentPeriodEndDateRequired and len(withDocumentPeriodEndDate) == 1:  # 4b
                chosen, step = withDocumentPeriodEndDate[0], "4b"
            else:
                quarters = max(round(days(c) / 91) for c in window)  # 4c
                longest = [c for c in window if round(days(c) / 91) == quarters]
                latestEnd = max(c.endDatetime for c in longest)  # 4d
                latestEnding = [c for c in longest if c.endDatetime == latestEnd]
                chosen = latestEnding[0]  # 4e: order of appearance
                step = "4c" if len(longest) == 1 else "4d" if len(latestEnding) == 1 else "4e"
    # steps 5 to 7: the latest end date in the first of these classes of durations that is present
    if chosen is None:
        oneDay = datetime.timedelta(days=1)
        for classStep, inClass in (("5", lambda c: c.endDatetime - c.startDatetime == oneDay),
                                   ("6", lambda c: days(c) < 28),
                                   ("7", lambda c: days(c) > 371)):
            inStep = [c for c in durations if inClass(c)]
            if inStep:
                latest = max(c.endDatetime for c in inStep)
                chosen = next(c for c in inStep if c.endDatetime == latest)  # order of appearance on a tie
                step = classStep
                break
    # step 8: order of appearance
    if chosen is None:
        chosen, step = durations[0], "8"
    return chosen, step


# The facts whose context is a fee exhibit's required context, in order of precedence, as proposed to the EXG
# author on 2026-09-20: ffd:FeeExhibitTp names the exhibit's own type, as dei:DocumentType does for a primary
# document; dei:EntityCentralIndexKey (required by EFM 6.5.21) and dei:EntityRegistrantName follow.
# ffd:SubmissnTp is optional for fee exhibits, so under the EXG author's principle it may not identify the
# required context; it stays a cross-check of the accompanying submission's type.
FEE_EXHIBIT_ANCHORS = ("FeeExhibitTp", "EntityCentralIndexKey", "EntityRegistrantName")


def selectFeeExhibitRequiredContext(eligibleContexts, anchorContexts, durationWindow,
                                    documentPeriodEndDateContexts, filingDate=None):
    """Select a fee exhibit's required context by its anchor facts, falling back to the ordering.

    The first anchor, in FEE_EXHIBIT_ANCHORS order, whose facts sit in one or more eligible duration contexts
    decides: one such context is the required context; several are put to selectRequiredContext, which
    chooses among them only.  When no anchor fact sits in an eligible duration, selectRequiredContext chooses
    among all eligible contexts as for any other submission.

    The filing-date bound is not applied to an anchor's context: the anchor is the filer's own designation of
    the exhibit's context, and a context ending after the filing date is then for the EXG 3.1.2 check to report
    rather than for the selection to pass over.

      eligibleContexts               contexts remaining after steps 1 and 2, in order of appearance
      anchorContexts                 sequence of (anchor local name, set of contexts holding that fact), in
                                     FEE_EXHIBIT_ANCHORS order
      durationWindow, documentPeriodEndDateContexts, filingDate
                                     as for selectRequiredContext

    Returns (requiredContext, step): step is "FE:" and the deciding anchor's local name, followed by "/" and
    the ordering's step when the ordering chose among the anchor's contexts, or the ordering's own step when no
    anchor decided.
    """
    for anchorName, contexts in anchorContexts:
        anchored = [c for c in eligibleContexts
                    if c in contexts and c.isStartEndPeriod and c.startDatetime is not None and c.endDatetime is not None]
        if len(anchored) == 1:
            return anchored[0], "FE:" + anchorName
        if anchored:
            chosen, step = selectRequiredContext(anchored, durationWindow, documentPeriodEndDateContexts, None)
            return chosen, "FE:{}/{}".format(anchorName, step)
    return selectRequiredContext(eligibleContexts, durationWindow, documentPeriodEndDateContexts, filingDate)


def contextPeriodText(cntx):
    """Period of a context for log records: "start..end (N days)", "instant end", "forever", or "" for None."""
    if cntx is None:
        return ""
    if cntx.isInstantPeriod:
        return "instant " + XmlUtil.dateunionValue(cntx.endDatetime, subtractOneDay=True)
    if cntx.isStartEndPeriod and cntx.startDatetime is not None and cntx.endDatetime is not None:
        return "{}..{} ({} days)".format(XmlUtil.dateunionValue(cntx.startDatetime),
                                         XmlUtil.dateunionValue(cntx.endDatetime, subtractOneDay=True),
                                         (cntx.endDatetime - cntx.startDatetime).days)
    return "forever"


def selectCoverAnchoredContext(eligibleContexts, anchorContexts, documentPeriodEndDates, primaryCik):
    """A cover-anchored selection of the required context, logged beside selectRequiredContext for comparison in
    batch runs (parameter requiredContextShadow=cover).  It does not affect validation.

    Proposed 2026-09-15 for testing against months and years of accepted filings: in the 2026-08 EDGAR XBRL feed the
    context holding dei:DocumentType was the ordering's choice for 99% of filings that have one, and most
    disagreements were the ordering overriding it.  Unlike the ordering, this uses only fact values and aspects
    (period, entity identifier, dimensions), never order of appearance or context ids, so it can be restated for a
    report without physical contexts.  Rules, in order (the rule that decides is returned):

      2              dei:DocumentType is in exactly one eligible duration: that duration, unless 3-dped's override
                     applies.  The dei:DocumentPeriodEndDate value is a date, which may differ from the context holding
                     it (a fund prospectus date), so it does not by itself move the selection.
      3-dped         its only duration holds no dei:DocumentPeriodEndDate fact, while other eligible durations hold one
                     and end on that fact's value (cover facts tagged in a stale context): those durations; or
                     DocumentType is in several eligible durations: those ending on a DocumentPeriodEndDate value
      3-<tie-break>  otherwise among those durations (those ending on a DocumentPeriodEndDate value when any does):
                     dimensions (fewest, i.e. the default legal entity), primaryCik (identifier = primary header
                     CIK), latest (end date), longest; unresolved only if contexts equal in all of these remain
      5-dped, 5-<tie-break>  no eligible duration holds DocumentType: the eligible durations ending on a
                     DocumentPeriodEndDate value, with the same tie-breaks
      6-instantOnly  DocumentType is only in eligible instants: the latest of them, reported although not a duration
      4-noCover      no DocumentType fact and no duration ending on a DocumentPeriodEndDate value (fee exhibits)
      4-ineligibleCover  DocumentType facts exist, but none is in an eligible context, and no fallback applies

    The anchor is dei:DocumentType as described, or alternatively the dei:EntityCentralIndexKey facts whose value is
    a submission CIK: a fee exhibit has EntityCentralIndexKey and no DocumentType, and elsewhere the two are normally
    in the same context.  The rules are the same for either anchor.

    Arguments:
      eligibleContexts        contexts remaining after steps 1 and 2 (requiredContextEligibleContexts)
      anchorContexts          set of contexts holding an anchor fact (dei:DocumentType, or dei:EntityCentralIndexKey)
      documentPeriodEndDates  dict of each context holding a dei:DocumentPeriodEndDate fact: set of its yyyy-mm-dd values
      primaryCik              primary submission header CIK, or None

    Returns (context or None, rule).
    """
    def endDate(cntx):  # yyyy-mm-dd of the last day of the period; a date-only end is held as the next midnight
        end = cntx.endDatetime
        if getattr(end, "dateOnly", (end.hour, end.minute, end.second, end.microsecond) == (0, 0, 0, 0)):
            end = end - datetime.timedelta(days=1)
        return end.date().isoformat()

    def identifier(cntx):
        entityIdentifier = cntx.entityIdentifier
        return ((entityIdentifier[1] if entityIdentifier else None) or "").strip()

    def decide(candidates, rulePrefix):
        for tieBreak, key in (("dimensions", lambda c: -len(c.qnameDims)),
                              ("primaryCik", lambda c: bool(primaryCik) and identifier(c) == primaryCik),
                              ("latest", lambda c: c.endDatetime),
                              ("longest", lambda c: c.endDatetime - c.startDatetime)):
            best = max(key(c) for c in candidates)
            candidates = [c for c in candidates if key(c) == best]
            if len(candidates) == 1:
                return candidates[0], f"{rulePrefix}-{tieBreak}"
        return min(candidates, key=lambda c: c.id), f"{rulePrefix}-unresolved"  # equal in every aspect compared

    eligible = [c for c in eligibleContexts if c.endDatetime is not None]
    durations = [c for c in eligible if c.isStartEndPeriod and c.startDatetime is not None]
    documentPeriodEndDateValues = set().union(*documentPeriodEndDates.values())
    dated = [c for c in durations if endDate(c) in documentPeriodEndDateValues]
    anchors = [c for c in durations if c in anchorContexts]
    if anchors:
        if len(anchors) == 1:
            anchor = anchors[0]
            selfDated = [c for c in durations
                         if c is not anchor and endDate(c) in documentPeriodEndDates.get(c, ())]
            if anchor in documentPeriodEndDates or not selfDated:
                return anchor, "2"
            candidates = selfDated
        else:
            candidates = [c for c in anchors if c in dated] or anchors
            if len(candidates) == len(anchors):  # not narrowed by DocumentPeriodEndDate
                return decide(candidates, "3")
        if len(candidates) == 1:
            return candidates[0], "3-dped"
        return decide(candidates, "3")
    if dated:
        return (dated[0], "5-dped") if len(dated) == 1 else decide(dated, "5")
    instants = [c for c in eligible if c.isInstantPeriod and c in anchorContexts]
    if instants:
        return max(instants, key=lambda c: c.endDatetime), "6-instantOnly"
    return None, ("4-ineligibleCover" if anchorContexts else "4-noCover")
