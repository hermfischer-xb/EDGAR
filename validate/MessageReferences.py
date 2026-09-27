"""
See COPYRIGHT.md for copyright information.

The references a table-driven (dei-validations.json, ft-validations.json) message carries, and the codes formed
from them.  The functions take plain values rather than the validation state, so that they can be tested without
loading a filing.

An entry may carry an EDGAR Filer Manual section ("efm": "6.5.20"), another guide's section ("msgSection":
"EXG:3.1.5", for the EDGAR XBRL Guide), or both.  Every reference the entry has becomes a message argument
(efmSection, exgSection), so converting a validation to EXG adds the EXG reference rather than replacing the
EFM one.  Which reference forms the message code, and with it the edgarCode and the numeric ID, is decided by
messageCodeLeadingGuide for all entries alike: while it is "EFM", an entry with an EFM reference keeps the
code it has always had, and only an entry with no EFM reference takes its code from the other guide.  When EFM
is retired, setting it to "EXG" moves every entry with an EXG reference to its EXG code without editing entries.
"""
import regex as re

messageCodeLeadingGuide = "EFM" # the guide whose reference forms the message code when an entry has more than one

# the part of a message key before its code suffix, e.g. "dq-{efmSection}" in "dq-{efmSection}-{tag}-Value"
messageKeySectionPattern = re.compile(r"(.*[{]efmSection[}]|[a-z]{2}-[0-9]{4}|dq-)(.*)")

def sectionCodeParts(section):
    """Levels of a section number as they appear in codes: numeric levels after the first are two digits,
    e.g. "6.5.2" -> ["6", "05", "02"], "3.1.24.2" -> ["3", "01", "24", "02"], "ft.oClmSrc" -> ["ft", "oClmSrc"]."""
    return [level.zfill(2) if i > 0 and level.isnumeric() else level
            for i, level in enumerate(section.split("."))]

def messageSectionArgs(efm, msgSection, leadingGuide=messageCodeLeadingGuide):
    """Message arguments for an entry's references.

    efm: the EFM section, e.g. "6.5.20" or "ft.oClmSrc", or None
    msgSection: another guide's section as "prefix:section", e.g. "EXG:3.1.5", or None
    Returns efmSection ("60520") and <prefix>Section ("exgSection": "30105") for each reference present, and
    arelleCode, the code prefix ("EFM.6.05.20", "EXG.3.01.05"), from the leading guide's reference when the entry
    has one, otherwise from EFM, otherwise from the other guide.  Returns no arelleCode when there is no reference.
    """
    args = {}
    codes = {}
    if efm:
        levels = sectionCodeParts(efm)
        args["efmSection"] = "".join(levels)
        codes["EFM"] = ".".join(["EFM"] + levels)
    if msgSection:
        guide, _sep, number = msgSection.partition(":")
        levels = sectionCodeParts(number)
        args[f"{guide.lower()}Section"] = "".join(levels)
        codes[guide] = ".".join([guide] + levels)
    for guide in (leadingGuide, "EFM", *codes):
        if guide in codes:
            args["arelleCode"] = codes[guide]
            break
    return args

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
