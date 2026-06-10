"""Stage 7 - Dashboard payload: one consolidated JSON the UI consumes.

Everything the stakeholder dashboard needs in a single file
(output/dashboard.json), regenerated on every pipeline run:

  deal            what is being sold, seller claims
  kpis            the headline tiles
  findings        curated analyst findings (title chain, disputes, estates)
  reconciliation  claimed vs verified per year + bridge + concentration
  coverage        statement matrix with exact missing periods
  scorecard       18-class gap analysis
  hygiene         duplicates / zero-byte / mismatches / forward-dated
  requisitions    flat prioritized list
  parties         the same requisitions grouped per counterparty, so the UI
                  can render a dedicated view per party involved
  recommendation  verdict + closing conditions
"""

from __future__ import annotations

from datetime import datetime


def build_dashboard(manifest, coverage, recon, scorecard, requisitions,
                    claims, findings) -> dict:
    years = sorted(y for y, v in recon["by_year"].items() if v["claimed"])
    conc = recon.get("concentration") or {}

    kpis = {
        "files_processed": manifest["total_files"],
        "files_by_extension": manifest["by_extension"],
        "requirements": {
            "satisfied": scorecard["satisfied"],
            "partial": scorecard["partial"],
            "missing": scorecard["missing"],
            "total": scorecard["total"],
            "headline": scorecard["headline"],
        },
        "statement_coverage_pct": coverage["overall_coverage_pct"],
        "statements_missing": coverage["total_missing_statements"],
        "fully_absent_societies": coverage["fully_absent_societies"],
        "hygiene": {
            "duplicate_groups": len(manifest["duplicate_groups"]),
            "zero_byte_files": len(manifest["zero_byte_files"]),
            "extension_mismatches": len(manifest["extension_mismatches"]),
            "forward_dated": len(manifest["future_dated"]),
        },
    }
    if years:
        y = years[0]
        v = recon["by_year"][y]
        kpis["revenue"] = {
            "reference_year": y,
            "claimed": v["claimed"],
            "verified_low": v["verified_low"],
            "verified_high": v["verified_high"],
            "overstatement_pct_low": v["overstatement_pct_low"],
            "overstatement_pct_high": v["overstatement_pct_high"],
        }
    if conc:
        kpis["concentration"] = {
            "top_song": conc["top_song"],
            "top_song_share": conc["top_song_share"],
            "claimed_top_song_share": conc.get("claimed_top_song_share"),
            "top5_share": conc["top5_share"],
            "claimed_top5_share": conc.get("claimed_top5_share"),
        }

    parties: dict[str, dict] = {}
    for r in requisitions:
        p = parties.setdefault(r["counterparty"], {"requests": [], "open_count": 0,
                                                   "highest_priority": "P2"})
        p["requests"].append(r)
        p["open_count"] += 1
        if r["priority"] < p["highest_priority"]:
            p["highest_priority"] = r["priority"]

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "deal": {
            "name": claims.get("deal_name"),
            "seller": claims.get("seller"),
            "seller_history": claims.get("seller_history"),
            "seller_contact": claims.get("seller_contact"),
            "seller_counsel": claims.get("seller_counsel"),
            "offered": claims.get("offered"),
            "excluded": claims.get("excluded"),
            "works_offered": claims.get("works_offered"),
            "claimed_revenue": claims.get("claimed_revenue"),
        },
        "kpis": kpis,
        "findings": {
            "title_chain": findings.get("title_chain"),
            "rights_disputes": findings.get("rights_disputes", []),
            "coverage_notes": findings.get("coverage_notes", []),
        },
        "reconciliation": {
            "by_year": recon["by_year"],
            "double_counted_settlements": recon["double_counted_settlements"],
            "accrued_never_received": recon["accrued_never_received"],
            "concentration": conc,
        },
        "coverage": coverage,
        "scorecard": scorecard["rows"],
        "hygiene": {
            "duplicate_groups": manifest["duplicate_groups"],
            "zero_byte_files": manifest["zero_byte_files"],
            "extension_mismatches": manifest["extension_mismatches"],
            "forward_dated": manifest["future_dated"],
            "misfiled": coverage["misfiled"],
            "invalid_periods": coverage["invalid_periods"],
        },
        "requisitions": requisitions,
        "parties": parties,
        "recommendation": findings.get("recommendation"),
    }
