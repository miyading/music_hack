"""Stage 5 - Requisitions: turn every gap into a concrete, prioritized
request addressed to the right counterparty. This doubles as the standing
requisition log sent to the seller: when documents arrive, the pipeline
re-runs and the list shrinks automatically.
"""

from __future__ import annotations

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def build_requisitions(scorecard: dict, coverage: dict) -> list[dict]:
    rows = []
    for r in scorecard["rows"]:
        if r["status"] == "SATISFIED":
            continue
        rows.append({
            "priority": r["priority"],
            "counterparty": r["counterparty"],
            "request": r["request"],
            "status": r["status"],
            "detail": r["note"],
        })

    # Specific statement re-issue requests, per society, with exact periods
    for soc, m in coverage["matrix"].items():
        if not m["missing"]:
            continue
        periods = ", ".join(m["missing"][:12])
        if len(m["missing"]) > 12:
            periods += f" (+{len(m['missing']) - 12} more)"
        rows.append({
            "priority": "P1",
            "counterparty": soc,
            "request": f"Reissue duplicate statements for: {periods}",
            "status": "GAP",
            "detail": f"{m['present']}/{m['expected']} periods on file ({m['coverage_pct']}%)",
        })

    for mf in coverage["misfiled"]:
        rows.append({
            "priority": "P2",
            "counterparty": "Seller (data room admin)",
            "request": f"Confirm and refile {mf['path']} (belongs to {mf['belongs_to']}, "
                       f"filed under {mf['filed_under']})",
            "status": "HYGIENE",
            "detail": "misfiled statement",
        })

    rows.sort(key=lambda r: (PRIORITY_ORDER.get(r["priority"], 9), r["counterparty"]))
    return rows
