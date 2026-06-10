"""Stage 1 - Manifest: fingerprint every file in the data room.

Detects: byte-identical duplicates (same content, different filenames),
zero-byte placeholders, files whose extension does not match their real
content (e.g. a JPG renamed .pdf), and forward-dated documents (filenames
or embedded issue dates in the future).
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from pathlib import Path

MAGIC = [
    (b"%PDF", "pdf"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG", "png"),
    (b"PK\x03\x04", "zip"),
    (b"GIF8", "gif"),
]

PLACEHOLDER_RE = re.compile(r"awaiting_upload|\.lock$|^~\$|placeholder|export_failed|failed_export", re.I)
HALF_YEAR_RE = re.compile(r"(?:2H|H2)[-_ ]?(?:FY)?(20\d{2})|(?:FY)?(20\d{2})[-_ ]?(?:2H|H2)", re.I)
YEAR_RE = re.compile(r"(?:FY)?(20\d{2})")
TEXT_DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d{2})")
ISO_DATE_RE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")

MONTHS = {m.lower()[:3]: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}


def sniff(path: Path) -> str:
    try:
        head = path.open("rb").read(16)
    except OSError:
        return "unreadable"
    for magic, kind in MAGIC:
        if head.startswith(magic):
            return kind
    return "text/other"


def _embedded_future_date(path: Path, today: date) -> str | None:
    """Scan the first 4KB of text-like content for an issue date in the future."""
    try:
        blob = path.open("rb").read(4096).decode("latin-1", errors="ignore")
    except OSError:
        return None
    candidates: list[date] = []
    for d, mon, y in TEXT_DATE_RE.findall(blob):
        m = MONTHS.get(mon.lower()[:3])
        if m:
            try:
                candidates.append(date(int(y), m, int(d)))
            except ValueError:
                pass
    for y, m, d in ISO_DATE_RE.findall(blob):
        try:
            candidates.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    future = [c for c in candidates if c > today]
    return max(future).isoformat() if future else None


def _filename_future_period(name: str, today: date) -> bool:
    m = HALF_YEAR_RE.search(name)
    if m:
        year = int(m.group(1) or m.group(2))
        # H2 of <year> ends 31 Dec; flag if that period hasn't started/finished plausibly
        if year > today.year or (year == today.year and today.month <= 6):
            return True
    return any(int(y) > today.year for y in YEAR_RE.findall(name))


def build_manifest(dataroom: Path, today: date | None = None) -> dict:
    today = today or date.today()
    files = []
    by_hash: dict[str, list[str]] = {}

    for p in sorted(dataroom.rglob("*")):
        if not p.is_file() or p.name == ".DS_Store":
            continue
        rel = str(p.relative_to(dataroom))
        size = p.stat().st_size
        ext = p.suffix.lower().lstrip(".")
        flags = []

        if size == 0:
            md5, kind = None, "empty"
            flags.append("zero_byte")
        else:
            md5 = hashlib.md5(p.read_bytes()).hexdigest()
            kind = sniff(p)
            by_hash.setdefault(md5, []).append(rel)

        if PLACEHOLDER_RE.search(p.name):
            flags.append("placeholder_name")
        if ext == "pdf" and kind not in ("pdf", "empty"):
            flags.append(f"extension_mismatch:{kind}")
        if _filename_future_period(p.name, today):
            flags.append("future_dated_filename")
        if size and kind in ("pdf", "text/other"):
            fd = _embedded_future_date(p, today)
            if fd:
                flags.append(f"future_issue_date:{fd}")

        files.append({"path": rel, "size": size, "ext": ext, "md5": md5,
                      "detected_type": kind, "flags": flags})

    dup_groups = [{"md5": h, "count": len(ps), "paths": ps}
                  for h, ps in sorted(by_hash.items()) if len(ps) > 1]

    flagged = [f for f in files if f["flags"]]
    return {
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "total_files": len(files),
        "by_extension": _count_by(files, "ext"),
        "duplicate_groups": dup_groups,
        "zero_byte_files": [f["path"] for f in files if "zero_byte" in f["flags"]],
        "extension_mismatches": [f["path"] for f in files
                                 if any(x.startswith("extension_mismatch") for x in f["flags"])],
        "future_dated": [f["path"] for f in files
                         if any(x.startswith("future") for x in f["flags"])],
        "flagged_files": flagged,
        "files": files,
    }


def _count_by(files: list[dict], key: str) -> dict:
    out: dict[str, int] = {}
    for f in files:
        out[f[key] or "(none)"] = out.get(f[key] or "(none)", 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))
