#!/usr/bin/env bash
# Extract every PDF in the data room to plain text (layout-preserving).
# Usage: ./01_extract.sh <data_room_dir> <output_text_dir>
set -u
SRC="${1:?data room dir}"; OUT="${2:?output text dir}"
mkdir -p "$OUT"
ERRLOG="$OUT/../extract_errors.log"; : > "$ERRLOG"
cd "$SRC"
find . -type f -name "*.pdf" -print0 | while IFS= read -r -d '' f; do
  rel="${f#./}"
  safe=$(echo "$rel" | tr '/ ' '__')
  pdftotext -layout "$f" "$OUT/${safe%.pdf}.txt" 2>>"$ERRLOG" \
    || echo "FAILED: $rel" >> "$ERRLOG"   # failures are findings, not noise
done
echo "extracted: $(ls "$OUT" | wc -l) · failures logged to $ERRLOG"
