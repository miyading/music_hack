"""Stage 2 - Coverage: build the statement coverage matrix.

For every collection society we know the expected cadence (quarterly /
half-yearly / yearly) and the expected date range. We parse every statement
filename in the room, mark each expected period present or missing, and flag
files that are misfiled (society in the filename does not match the folder)
or carry impossible periods (e.g. a 13th month).
"""

from __future__ import annotations

import re
from pathlib import Path

PERIOD_RE = re.compile(r"(20\d{2})(?:[-_](Q[1-4]|H[12]|\d{2}))?", re.I)


def expected_periods(cadence: str, start: int, end: int) -> list[str]:
    out = []
    for y in range(start, end + 1):
        if cadence == "quarterly":
            out += [f"{y}-Q{q}" for q in range(1, 5)]
        elif cadence == "half":
            out += [f"{y}-H1", f"{y}-H2"]
        else:  # yearly
            out.append(str(y))
    return out


def _parse_period(name: str) -> str | None:
    m = PERIOD_RE.search(name)
    if not m:
        return None
    year, per = m.group(1), m.group(2)
    if not per:
        return year
    per = per.upper()
    if per.isdigit():  # monthly -> keep as-is, validity checked separately
        return f"{year}-{per}"
    return f"{year}-{per}"


def _token_in(name: str, token: str) -> bool:
    return re.search(rf"(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])", name, re.I) is not None


def build_coverage(dataroom: Path, societies_cfg: dict) -> dict:
    societies = societies_cfg["societies"]
    distributors = societies_cfg.get("distributors", [])
    roots = societies_cfg.get("statement_roots", ["statements", "distributors"])
    all_tokens = list(societies) + distributors

    stmt_files = []
    for root in roots:
        base = dataroom / root
        if base.is_dir():
            stmt_files += [p for p in base.rglob("*") if p.is_file()]

    found: dict[str, set[str]] = {s: set() for s in societies}
    misfiled, invalid_periods = [], []

    for p in stmt_files:
        rel = str(p.relative_to(dataroom))
        name_token = next((t for t in all_tokens if _token_in(p.stem, t)), None)
        folder_token = next((t for t in all_tokens
                             if any(_token_in(part, t) for part in p.parent.parts)), None)
        token = name_token or folder_token
        period = _parse_period(p.name)

        if name_token and folder_token and name_token != folder_token:
            misfiled.append({"path": rel, "belongs_to": name_token, "filed_under": folder_token})
        m = re.search(r"20\d{2}[-_](\d{2})\b", p.name)
        if m and int(m.group(1)) > 12:
            invalid_periods.append({"path": rel, "reason": f"month {m.group(1)} does not exist"})
        if p.stat().st_size == 0:
            continue  # zero-byte file is not evidence of coverage
        if token in societies and period:
            found[token].add(period)

    matrix, total_expected, total_present = {}, 0, 0
    for soc, cfg in societies.items():
        exp = expected_periods(cfg["cadence"], cfg["start"], cfg["end"])
        present = sorted(found[soc] & set(exp))
        missing = [x for x in exp if x not in found[soc]]
        total_expected += len(exp)
        total_present += len(present)
        matrix[soc] = {
            "territory": cfg.get("territory", ""),
            "cadence": cfg["cadence"],
            "expected": len(exp),
            "present": len(present),
            "missing": missing,
            "coverage_pct": round(len(present) / len(exp) * 100, 1) if exp else 100.0,
        }

    return {
        "matrix": matrix,
        "overall_coverage_pct": round(total_present / total_expected * 100, 1) if total_expected else 0,
        "total_missing_statements": total_expected - total_present,
        "fully_absent_societies": [s for s, v in matrix.items() if v["present"] == 0],
        "misfiled": misfiled,
        "invalid_periods": invalid_periods,
    }
