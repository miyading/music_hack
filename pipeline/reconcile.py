"""Stage 3 - Reconcile: rebuild revenue bottom-up from the seller's own
statement detail and compare it with the headline numbers in the CIM /
summary schedules.

Detections:
  * label gross receipts booked as publishing revenue (only a royalty %
    of those receipts is actually the publisher's)
  * one-off settlements double-counted across years (same description +
    amount appearing in more than one year)
  * accrued / black-box estimates never actually received
  * per-song concentration vs the disclosed concentration
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

AMOUNT_COLS = ["amount_usd", "amount", "net_amount", "net", "royalty", "payable_usd"]
SONG_COLS = ["song", "work_title", "title", "composition"]
YEAR_RE = re.compile(r"(20\d{2})")

ROYALTY_TYPES = {"royalty", "performance", "mechanical", "sync", "digital", "society_total"}
GROSS_TYPES = {"label_gross_receipts", "label_gross", "gross_receipts"}
SETTLEMENT_TYPES = {"settlement", "one_off", "one-off"}
ACCRUED_TYPES = {"accrued", "black_box", "black-box", "estimate", "pipeline"}


def _col(row: dict, names: list[str]) -> str | None:
    for n in names:
        for k in row:
            if k and k.strip().lower() == n:
                return k
    return None


def _rows(path: Path):
    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            yield from csv.DictReader(fh)
    except (OSError, csv.Error, UnicodeDecodeError):
        return


def _year_of(path: Path, row: dict) -> int | None:
    if row.get("year"):
        try:
            return int(row["year"])
        except ValueError:
            pass
    m = YEAR_RE.search(path.name)
    return int(m.group(1)) if m else None


def build_reconciliation(dataroom: Path, claims: dict, societies_cfg: dict) -> dict:
    roots = societies_cfg.get("statement_roots", ["statements", "distributors"])
    rate = claims.get("label_royalty_rate", 0.18)

    detail = defaultdict(float)            # year -> verified statement detail
    per_song = defaultdict(lambda: defaultdict(float))
    label_gross = defaultdict(float)
    accrued = defaultdict(list)
    settlements = []                       # (desc, amount, year, path, source)
    summary_claims = defaultdict(float)    # year -> seller summary total
    summary_items = defaultdict(list)

    def classify(path: Path, row: dict, is_summary: bool):
        amt_col = _col(row, AMOUNT_COLS)
        if not amt_col:
            return
        try:
            amt = float(str(row[amt_col]).replace(",", "").replace("$", ""))
        except ValueError:
            return
        year = _year_of(path, row)
        if year is None:
            return
        rtype = (row.get("type") or "royalty").strip().lower()
        desc = (row.get("description") or row.get("source") or "").strip()

        if is_summary:
            summary_claims[year] += amt
            summary_items[year].append({"description": desc, "type": rtype, "amount": amt})
            if rtype in SETTLEMENT_TYPES:
                settlements.append((desc.lower(), round(amt), year, str(path), "summary"))
            return

        if rtype in GROSS_TYPES:
            label_gross[year] += amt
        elif rtype in SETTLEMENT_TYPES:
            settlements.append((desc.lower(), round(amt), year, str(path), "detail"))
        elif rtype in ACCRUED_TYPES:
            accrued[year].append({"description": desc, "amount": amt})
        else:
            detail[year] += amt
            song_col = _col(row, SONG_COLS)
            if song_col and row[song_col]:
                per_song[year][row[song_col].strip()] += amt

    for p in sorted(dataroom.rglob("*.csv")):
        rel = p.relative_to(dataroom)
        is_summary = "summar" in str(rel).lower()
        in_roots = any(str(rel).startswith(r + "/") or str(rel).startswith(r) for r in roots)
        if not (is_summary or in_roots or "settlement" in str(rel).lower()):
            continue
        for row in _rows(p):
            classify(rel, row, is_summary)

    # Settlement double-counting: same description+amount in >1 year
    groups = defaultdict(list)
    for desc, amt, year, path, src in settlements:
        groups[(desc, amt)].append({"year": year, "path": path, "source": src})
    double_counted = [
        {"description": k[0], "amount": k[1], "occurrences": v}
        for k, v in groups.items() if len({o["year"] for o in v}) > 1
    ]
    settlement_once = defaultdict(float)
    for (desc, amt), occ in groups.items():
        settlement_once[min(o["year"] for o in occ)] += amt

    years = sorted(set(detail) | set(summary_claims) | {int(y) for y in claims.get("claimed_revenue", {})})
    by_year = {}
    for y in years:
        low = detail[y] + settlement_once.get(y, 0.0)
        high = low + label_gross[y] * rate
        claimed = claims.get("claimed_revenue", {}).get(str(y)) or summary_claims.get(y) or 0
        entry = {
            "statement_detail": round(detail[y], 2),
            "settlements_counted_once": round(settlement_once.get(y, 0.0), 2),
            "label_gross_receipts": round(label_gross[y], 2),
            "label_royalty_entitlement": round(label_gross[y] * rate, 2),
            "accrued_excluded": round(sum(a["amount"] for a in accrued[y]), 2),
            "verified_low": round(low, 2),
            "verified_high": round(high, 2),
            "claimed": round(claimed, 2),
        }
        if claimed and high:
            entry["overstatement_pct_low"] = round((claimed / high - 1) * 100, 1)
            entry["overstatement_pct_high"] = round((claimed / low - 1) * 100, 1)
            entry["bridge"] = _bridge(claimed, low, label_gross[y], rate,
                                      double_counted, accrued[y], y)
        by_year[y] = entry

    concentration = _concentration(per_song, claims)
    return {
        "label_royalty_rate": rate,
        "by_year": by_year,
        "double_counted_settlements": double_counted,
        "accrued_never_received": {y: v for y, v in accrued.items() if v},
        "concentration": concentration,
    }


def _bridge(claimed, verified_low, gross, rate, double_counted, accrued_rows, year):
    items = []
    if gross:
        items.append({"item": "Label gross receipts booked as publishing revenue "
                              f"(publisher entitled to ~{rate:.0%} royalty only)",
                      "amount": round(gross * (1 - rate), 2)})
    for dc in double_counted:
        if any(o["year"] == year and o["source"] == "summary" for o in dc["occurrences"]):
            items.append({"item": f"Settlement double-counted: {dc['description']}",
                          "amount": dc["amount"]})
    for a in accrued_rows:
        items.append({"item": f"Accrued/black-box never received: {a['description']}",
                      "amount": a["amount"]})
    explained = sum(i["amount"] for i in items)
    return {"gap": round(claimed - verified_low, 2), "items": items,
            "explained": round(explained, 2),
            "residual_unexplained": round(claimed - verified_low - explained, 2)}


def _concentration(per_song, claims) -> dict:
    complete_years = [y for y, songs in per_song.items() if songs]
    if not complete_years:
        return {}
    out = {}
    for y in sorted(complete_years):
        songs = per_song[y]
        total = sum(songs.values())
        ranked = sorted(songs.items(), key=lambda kv: -kv[1])
        out[y] = {
            "total": round(total, 2),
            "top_song": ranked[0][0],
            "top_song_share": round(ranked[0][1] / total, 4),
            "top5_share": round(sum(v for _, v in ranked[:5]) / total, 4),
            "top5": [{"song": s, "amount": round(v, 2), "share": round(v / total, 4)}
                     for s, v in ranked[:5]],
        }
    claimed_years = [int(y) for y in claims.get("claimed_revenue", {}) if int(y) in out]
    latest = max(claimed_years) if claimed_years else max(y for y in out if out[y]["total"] > 0)
    return {
        "by_year": out,
        "reference_year": latest,
        "top_song": out[latest]["top_song"],
        "top_song_share": out[latest]["top_song_share"],
        "claimed_top_song_share": claims.get("claimed_top_song_share"),
        "top5_share": out[latest]["top5_share"],
        "claimed_top5_share": claims.get("claimed_top5_share"),
    }
