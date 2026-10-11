#!/bin/sh
# Rebuild the EXG resources from the guide's Word source.  See ../handoffs/README.md.
#   sh build.sh <guide.docx> "<edition>" "<review note>" [work dir]
# Writes validate/resources/exg-set-definitions.json and efm-exg-references.json, and in the work dir the extracted
# tables (guide.json), the crosswalk and fresh reference candidates.  The candidates are NOT used until reviewed:
# compare work/refs/candidates.tsv with references-candidates.tsv, settle the differences in review, then copy it
# over references-candidates.tsv and run this again.
set -e
DOCX=${1:?guide .docx}; EDITION=${2:?edition, e.g. "September 2026 draft (xbrl-guide_Sept26.docx)"}; REVIEW=${3:?review note}
HERE=$(cd "$(dirname "$0")" && pwd); VALIDATE=$(cd "$HERE/../../.." && pwd); WORK=${4:-$(mktemp -d)}
python3 "$HERE/extractSets.py" "$DOCX" "$VALIDATE/resources/exg-set-definitions.json" "$EDITION"
python3 "$HERE/extract.py" "$DOCX" "$WORK/guide.json"
python3 "$VALIDATE/tools/crosswalk.py" "$VALIDATE" "$WORK/guide.json" "$WORK/crosswalk"
python3 "$VALIDATE/tools/references.py" "$WORK/crosswalk" "$WORK/guide.json" "$VALIDATE" "$WORK/refs"
python3 "$HERE/buildReferences.py" "$HERE/references-candidates.tsv" "$EDITION" "$REVIEW" "$VALIDATE/resources/efm-exg-references.json"
if cmp -s "$WORK/refs/candidates.tsv" "$HERE/references-candidates.tsv"; then
    echo "reference candidates unchanged"
else
    echo "reference candidates CHANGED: review $WORK/refs/candidates.tsv against $HERE/references-candidates.tsv"
fi
echo "work files in $WORK"
