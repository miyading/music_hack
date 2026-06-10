"""Stage 6 - Report: synthesize every stage into a single stakeholder-facing
markdown report (KPIs, hygiene, reconciliation bridge, coverage matrix,
scorecard, requisition log, recommendation).
"""

from __future__ import annotations

from datetime import date


def _money(x: float) -> str:
    return f"${x:,.0f}"


def _kpi_block(manifest, coverage, recon, scorecard, claims) -> str:
    years = sorted(y for y, v in recon["by_year"].items() if v["claimed"])
    lines = ["| Metric | Value |", "|---|---|"]
    lines.append(f"| Files processed | {manifest['total_files']} "
                 f"({', '.join(f'{v} {k}' for k, v in list(manifest['by_extension'].items())[:3])}) |")
    if years:
        y = years[0]
        v = recon["by_year"][y]
        lines.append(f"| Claimed FY{y} revenue | {_money(v['claimed'])} |")
        lines.append(f"| Verified FY{y} base | {_money(v['verified_low'])}–{_money(v['verified_high'])} "
                     f"(overstated {v['overstatement_pct_low']}–{v['overstatement_pct_high']}%) |")
    conc = recon.get("concentration") or {}
    if conc:
        claimed = conc.get("claimed_top_song_share")
        lines.append(f"| Top-song concentration | {conc['top_song_share']:.0%} "
                     f"(\"{conc['top_song']}\"){f' — disclosed as ~{claimed:.0%}' if claimed else ''} |")
    lines.append(f"| Fund requirements met | {scorecard['headline']} |")
    lines.append(f"| Statement coverage | {coverage['overall_coverage_pct']}% — "
                 f"{coverage['total_missing_statements']} statements missing"
                 f"{'; fully absent: ' + ', '.join(coverage['fully_absent_societies']) if coverage['fully_absent_societies'] else ''} |")
    lines.append(f"| Data hygiene flags | {len(manifest['duplicate_groups'])} duplicate groups · "
                 f"{len(manifest['zero_byte_files'])} zero-byte files · "
                 f"{len(manifest['extension_mismatches'])} content/extension mismatches · "
                 f"{len(manifest['future_dated'])} forward-dated documents |")
    return "\n".join(lines)


def build_report(manifest, coverage, recon, scorecard, requisitions, claims) -> str:
    out = []
    out.append(f"# {claims.get('deal_name', 'Catalog')} — Due Diligence Findings")
    out.append(f"*Automated data-room audit · seller: {claims.get('seller', 'n/a')} · "
               f"generated {date.today().isoformat()}*\n")

    out.append("## Headline\n")
    out.append(_kpi_block(manifest, coverage, recon, scorecard, claims))

    out.append("\n## 1. What is for sale\n")
    out.append(f"**Offered:** {claims.get('offered', 'n/a')}\n")
    out.append(f"**Excluded:** {claims.get('excluded', 'n/a')}\n")

    out.append("## 2. Revenue reconciliation\n")
    out.append("| Year | Claimed | Statement detail | + Label royalty entitlement | Verified range | Overstatement |")
    out.append("|---|---|---|---|---|---|")
    for y, v in sorted(recon["by_year"].items()):
        over = (f"{v['overstatement_pct_low']}–{v['overstatement_pct_high']}%"
                if v.get("overstatement_pct_low") is not None and v["claimed"] else "—")
        out.append(f"| {y} | {_money(v['claimed']) if v['claimed'] else '—'} "
                   f"| {_money(v['verified_low'])} | {_money(v['label_royalty_entitlement'])} "
                   f"| {_money(v['verified_low'])}–{_money(v['verified_high'])} | {over} |")

    for y, v in sorted(recon["by_year"].items()):
        bridge = v.get("bridge")
        if not bridge:
            continue
        out.append(f"\n**FY{y} bridge — claimed {_money(v['claimed'])} vs verified {_money(v['verified_low'])} "
                   f"(gap {_money(bridge['gap'])}):**\n")
        for item in bridge["items"]:
            out.append(f"- {_money(item['amount'])} — {item['item']}")
        out.append(f"- {_money(bridge['residual_unexplained'])} — residual, unexplained "
                   "(consistent with writer-share double-counting on PRO lines; request per-song ledger)")

    if recon.get("double_counted_settlements"):
        out.append("\n**Double-counted one-offs:**\n")
        for dc in recon["double_counted_settlements"]:
            yrs = sorted({o["year"] for o in dc["occurrences"]})
            out.append(f"- \"{dc['description']}\" {_money(dc['amount'])} booked in "
                       f"{' and '.join(map(str, yrs))} — counted once")

    conc = recon.get("concentration") or {}
    if conc:
        out.append(f"\n**Concentration (FY{conc['reference_year']}):** top song "
                   f"\"{conc['top_song']}\" = {conc['top_song_share']:.1%} of verified earnings"
                   + (f" (disclosed ~{conc['claimed_top_song_share']:.0%})" if conc.get("claimed_top_song_share") else "")
                   + f"; top 5 = {conc['top5_share']:.1%}"
                   + (f" (disclosed ~{conc['claimed_top5_share']:.0%})" if conc.get("claimed_top5_share") else "") + ".\n")
        for s in conc["by_year"][conc["reference_year"]]["top5"]:
            out.append(f"- {s['song']}: {_money(s['amount'])} ({s['share']:.1%})")

    out.append("\n## 3. Data hygiene\n")
    if manifest["duplicate_groups"]:
        out.append(f"**{len(manifest['duplicate_groups'])} byte-identical duplicate groups**, e.g.:\n")
        for g in manifest["duplicate_groups"][:5]:
            out.append(f"- {g['count']} identical copies: {', '.join('`' + p + '`' for p in g['paths'])}")
    if manifest["extension_mismatches"]:
        out.append(f"\n**Content/extension mismatches:** "
                   + ", ".join(f"`{p}`" for p in manifest["extension_mismatches"]))
    if manifest["future_dated"]:
        out.append(f"\n**Forward-dated documents:** "
                   + ", ".join(f"`{p}`" for p in manifest["future_dated"]))
    if manifest["zero_byte_files"]:
        out.append(f"\n**{len(manifest['zero_byte_files'])} zero-byte placeholders**, e.g. "
                   + ", ".join(f"`{p}`" for p in manifest["zero_byte_files"][:6]))
    if coverage["misfiled"]:
        out.append("\n**Misfiled statements:**\n")
        for mf in coverage["misfiled"]:
            out.append(f"- `{mf['path']}` belongs to {mf['belongs_to']}, filed under {mf['filed_under']}")
    if coverage["invalid_periods"]:
        out.append("\n**Impossible periods:**\n")
        for ip in coverage["invalid_periods"]:
            out.append(f"- `{ip['path']}` — {ip['reason']}")

    out.append("\n## 4. Statement coverage matrix\n")
    out.append("| Society | Territory | Expected | Present | Coverage | Missing periods |")
    out.append("|---|---|---|---|---|---|")
    for soc, m in coverage["matrix"].items():
        missing = ", ".join(m["missing"][:6])
        if len(m["missing"]) > 6:
            missing += f" (+{len(m['missing']) - 6} more)"
        out.append(f"| {soc} | {m['territory']} | {m['expected']} | {m['present']} "
                   f"| {m['coverage_pct']}% | {missing or '—'} |")
    out.append(f"\nOverall: **{coverage['overall_coverage_pct']}%** · "
               f"**{coverage['total_missing_statements']} statements missing**.")

    out.append("\n## 5. Gap analysis — fund requirements vs data room\n")
    out.append(f"**{scorecard['headline']}**\n")
    out.append("| # | Requirement | Status | Note |")
    out.append("|---|---|---|---|")
    for r in scorecard["rows"]:
        badge = {"SATISFIED": "OK", "PARTIAL": "PARTIAL", "MISSING": "MISSING"}[r["status"]]
        out.append(f"| {r['id']} | {r['name']} | **{badge}** | {r['note']} |")

    out.append("\n## 6. Requisition log (auto-regenerates on every re-run)\n")
    out.append("| Priority | Counterparty | Request | Detail |")
    out.append("|---|---|---|---|")
    for r in requisitions:
        out.append(f"| {r['priority']} | {r['counterparty']} | {r['request']} | {r['detail']} |")

    out.append("\n## 7. Recommendation\n")
    years = sorted(y for y, v in recon["by_year"].items() if v["claimed"])
    if years:
        y = years[0]
        v = recon["by_year"][y]
        conc_txt = (f", ~{conc['top_song_share']:.0%} single-song concentration" if conc else "")
        base = round(v["verified_low"] / 1000) * 1000
        out.append(f"**Do not proceed at the indicated basis.** Re-cut any offer off verified revenue "
                   f"(~{_money(base)} base{conc_txt}), with closing conditions: "
                   "executed chain of title; PRO re-registrations and back-payment quantification; "
                   "estate documentation; legible sample clearance; and a holdback/escrow covering "
                   "unquantified liabilities. Every received document goes back into the data room "
                   "and the pipeline re-scores until the scorecard is green.")
    out.append("")
    return "\n".join(out)
