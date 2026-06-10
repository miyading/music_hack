"""Stage 4 - Scorecard: score the data room against the fund's required
document classes (config/requirements.json).

Each "files"-type requirement is matched by regex against relative paths.
Matches hitting the invalid pattern (draft / unsigned / illegible / ...)
don't count as satisfying evidence. A nominally-valid file that is
byte-identical to an invalid one (e.g. "FINAL" == draft, same MD5) is
demoted too. "coverage"-type requirements are scored off the Stage 2 matrix.
"""

from __future__ import annotations

import re

SATISFIED, PARTIAL, MISSING = "SATISFIED", "PARTIAL", "MISSING"


def _score_files(req: dict, manifest: dict) -> tuple[str, str]:
    pats = [re.compile(p, re.I) for p in req["patterns"]]
    inval = re.compile(req["invalid_pattern"], re.I) if req.get("invalid_pattern") else None
    matches = [f for f in manifest["files"]
               if any(p.search(f["path"]) for p in pats) and "zero_byte" not in f["flags"]]

    if not matches:
        return MISSING, "none on file"

    invalid = [f for f in matches if inval and inval.search(f["path"])]
    valid = [f for f in matches if f not in invalid]

    # demote "valid" files that are byte-identical to an invalid copy
    invalid_md5 = {f["md5"] for f in invalid if f["md5"]}
    demoted = [f for f in valid if f["md5"] in invalid_md5]
    valid = [f for f in valid if f not in demoted]
    invalid += demoted

    notes = []
    if demoted:
        notes.append(f"{len(demoted)} file(s) byte-identical to a draft/invalid copy")
    if invalid and not demoted:
        notes.append(f"{len(invalid)} draft/unsigned/invalid file(s)")

    if not valid:
        status = req.get("all_invalid_status", MISSING)
        notes.insert(0, "only drafts/unsigned/invalid versions on file")
        return status, "; ".join(notes)

    status = SATISFIED
    min_count = req.get("min_count", 1)
    if len(valid) < min_count:
        status = PARTIAL
        notes.insert(0, f"{len(valid)}/{min_count} required documents present")
    if invalid:
        status = PARTIAL

    for extra in req.get("also_require", []):
        pat = re.compile(extra["pattern"], re.I)
        if not any(pat.search(f["path"]) for f in manifest["files"] if "zero_byte" not in f["flags"]):
            status = PARTIAL if status == SATISFIED else status
            notes.append(extra["note"])

    return status, "; ".join(notes) if notes else f"{len(valid)} document(s) on file"


def _score_coverage(req: dict, coverage: dict) -> tuple[str, str]:
    socs = req["societies"]
    rows = [coverage["matrix"][s] for s in socs if s in coverage["matrix"]]
    expected = sum(r["expected"] for r in rows)
    present = sum(r["present"] for r in rows)
    if expected == 0:
        return MISSING, "no expectations configured"
    pct = present / expected * 100
    missing_n = expected - present
    absent = [s for s in socs if coverage["matrix"].get(s, {}).get("present", 0) == 0]
    if present == 0:
        return MISSING, f"entire {'society' if len(socs) == 1 else 'class'} absent ({', '.join(socs)})"
    if missing_n == 0:
        return SATISFIED, "full coverage"
    note = f"~{pct:.0f}% coverage; {missing_n} statements missing"
    if absent:
        note += f"; fully absent: {', '.join(absent)}"
    return PARTIAL, note


def build_scorecard(requirements: list[dict], manifest: dict, coverage: dict) -> dict:
    rows = []
    for req in requirements:
        if req["type"] == "coverage":
            status, note = _score_coverage(req, coverage)
        else:
            status, note = _score_files(req, manifest)
        rows.append({
            "id": req["id"], "name": req["name"], "status": status, "note": note,
            "counterparty": req["counterparty"], "priority": req["priority"],
            "request": req["request"],
        })
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in (SATISFIED, PARTIAL, MISSING)}
    return {
        "rows": rows,
        "satisfied": counts[SATISFIED],
        "partial": counts[PARTIAL],
        "missing": counts[MISSING],
        "total": len(rows),
        "headline": f"{counts[SATISFIED]}/{len(rows)} fully satisfied · "
                    f"{counts[PARTIAL]} partial · {counts[MISSING]} missing",
    }
