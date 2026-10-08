"""
See COPYRIGHT.md for copyright information.

The references a table-driven (dei-validations.json, ft-validations.json) message carries, and the codes formed
from them.  The functions take plain values rather than the validation state, so that they can be tested without
loading a filing.

An entry may carry an EDGAR Filer Manual section ("efm": "6.5.20"), another guide's section ("msgSection":
"EXG:3.1.5", for the EDGAR XBRL Guide), or both.  Every reference the entry has becomes a message argument
(efmSection, exgSection), so converting a validation to EXG adds the EXG reference rather than replacing the
EFM one.  Which reference forms the message code, and with it the edgarCode and the numeric ID, is decided for all entries
alike by the messageCodes parameter, the guides in priority order (parseMessageCodes), default "EFM": with
"EFM", an entry with an EFM reference keeps the code it has always had, and only an entry with no EFM reference
takes its code from the other guide; with "EXG", every entry with an EXG reference takes its EXG code, without
editing entries.  Listing more than one guide, such as "EXG EFM", also gives each message its full code under
each listed guide it has a reference to, as arguments efmCode and exgCode (messageGuideCodes), so that runs coded
by different guides can be compared message by message.
"""
import regex as re

messageCodeLeadingGuide = "EFM" # the guide whose reference forms the message code when messageCodes is not given

# the part of a message key before its code suffix, e.g. "dq-{efmSection}" in "dq-{efmSection}-{tag}-Value"
messageKeySectionPattern = re.compile(r"(.*[{]efmSection[}]|[a-z]{2}-[0-9]{4}|dq-)(.*)")

def sectionCodeParts(section):
    """Levels of a section number as they appear in codes: numeric levels after the first are two digits,
    e.g. "6.5.2" -> ["6", "05", "02"], "3.1.24.2" -> ["3", "01", "24", "02"], "ft.oClmSrc" -> ["ft", "oClmSrc"]."""
    return [level.zfill(2) if i > 0 and level.isnumeric() else level
            for i, level in enumerate(section.split("."))]

def parseMessageCodes(value):
    """The messageCodes parameter: guides in priority order, e.g. ("EXG", "EFM"), from a list (JSON) or one
    blank-separated string (formula or GUI parameter); (messageCodeLeadingGuide,) when absent or empty."""
    if isinstance(value, str):
        value = value.split()
    guides = tuple(str(v).strip().upper() for v in (value or ()) if str(v).strip())
    return guides or (messageCodeLeadingGuide,)

def messageCodePrefixes(efm, msgSection):
    """{guide: code prefix} for an entry's references, e.g. {"EFM": "EFM.6.05.20", "EXG": "EXG.3.01.05"}."""
    codes = {}
    if efm:
        codes["EFM"] = ".".join(["EFM"] + sectionCodeParts(efm))
    if msgSection:
        guide, _sep, number = msgSection.partition(":")
        codes[guide] = ".".join([guide] + sectionCodeParts(number))
    return codes

def messageSectionArgs(efm, msgSection, leadingGuide=messageCodeLeadingGuide):
    """Message arguments for an entry's references.

    efm: the EFM section, e.g. "6.5.20" or "ft.oClmSrc", or None
    msgSection: another guide's section as "prefix:section", e.g. "EXG:3.1.5", or None
    leadingGuide: a guide, or guides in priority order as from parseMessageCodes
    Returns efmSection ("60520") and <prefix>Section ("exgSection": "30105") for each reference present, and
    arelleCode, the code prefix ("EFM.6.05.20", "EXG.3.01.05"), from the first leading guide the entry has a
    reference to, otherwise from EFM, otherwise from the other guide.  Returns no arelleCode when there is no
    reference.
    """
    args = {}
    codes = messageCodePrefixes(efm, msgSection)
    for guide, prefix in codes.items():
        args[f"{guide.lower()}Section"] = prefix.partition(".")[2].replace(".", "")
    leading = (leadingGuide,) if isinstance(leadingGuide, str) else tuple(leadingGuide)
    for guide in (*leading, "EFM", *codes):
        if guide in codes:
            args["arelleCode"] = codes[guide]
            break
    return args

def messageGuideCodes(messageKey, logArgs, efm, msgSection, guides):
    """When more than one guide is listed (messageCodes "EXG EFM"), the message's full code under each listed guide
    the entry has a reference to, as arguments efmCode and exgCode; otherwise none.  Raises KeyError as
    messageCode does."""
    if len(guides) < 2:
        return {}
    codes = messageCodePrefixes(efm, msgSection)
    return {f"{guide.lower()}Code": messageCode(messageKey, dict(logArgs, arelleCode=codes[guide]))
            for guide in guides if guide in codes}

def messageEdgarCode(messageKey, arelleCode):
    """The edgarCode argument: the message key with its {...} fields un-expanded.  When the code comes from a
    guide other than EFM, a "-{efmSection}" in the key is dropped, e.g. "dq-{efmSection}-{tag}-Value" becomes
    "dq-{tag}-Value" for an EXG-coded message."""
    guide = (arelleCode or "").partition(".")[0]
    if guide and guide != "EFM":
        return messageKey.replace("-{efmSection}", "")
    return messageKey

def messageCode(messageKey, logArgs):
    """The message code: arelleCode followed by the message key's suffix with its fields filled from logArgs,
    commas, periods and spaces removed, and the first letter after the suffix's first hyphen lowercased,
    e.g. "EFM.6.05.20" and "dq-{efmSection}-{tag}-Value" with tag "DocumentType" -> "EFM.6.05.20.documentTypeValue".
    Raises KeyError when logArgs lacks arelleCode or a field of the key."""
    m = messageKeySectionPattern.match(messageKey or "")
    keyAfterSection = m.group(2) if m else ""
    code = "{arelleCode}.".format(**logArgs) + keyAfterSection.format(**logArgs) \
           .replace(",", "").replace(".","").replace(" ","") # replace commas in names embedded in message code portion
    if code.endswith("."):
        code = code[:-1]
    codeSections = code.split("-")
    if len(codeSections) > 1 and codeSections[1]:
        codeSections[1] = codeSections[1][0].lower() + codeSections[1][1:] # start with lowercase
    return "".join(codeSections)
