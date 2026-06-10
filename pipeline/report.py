"""Stage 6 - Report: synthesize every stage into the stakeholder-facing
findings document, structured like the diligence deck:

  Headline KPIs
  1. What is for sale
  2. Headline findings
     2.1 Title chain (curated analyst findings, config/findings.json)
     2.2 Revenue reconciliation (computed)
     2.3 Fabricated / forward-dated documents (computed)
     2.4 Rights disputes & estates (curated)
     2.5 Statement coverage gaps (computed)
  3. Gap analysis - fund requirements vs data room
  4. Process to collect the missing documents
  5. Recommendation
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


def _section_title_chain(findings: dict) -> list[str]:
    tc = findings.get("title_chain")
    if not tc:
        return []
    out = [f"\n### 2.1 {tc['headline']}\n"]
    for b in tc["bullets"]:
        out.append(f"- {b}")
    cc = tc.get("composition_count")
    if cc:
        out.append(f"\n> **{cc['headline']}** {cc['note']}")
    return out


def _section_revenue(recon: dict) -> list[str]:
    out = ["\n### 2.2 Revenue reconciliation — price-defining\n"]
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
    return out


def _section_fabrication(manifest: dict, coverage: dict) -> list[str]:
    out = ["\n### 2.3 Evidence of fabricated or forward-dated documents\n"]
    for p in manifest["future_dated"]:
        out.append(f"- `{p}` — forward-dated (filename period or embedded issue date in the future)")
    for g in manifest["duplicate_groups"][:5]:
        out.append(f"- {g['count']} byte-identical copies (same MD5): "
                   + ", ".join(f"`{p}`" for p in g["paths"]))
    for p in manifest["extension_mismatches"]:
        out.append(f"- `{p}` — content does not match extension (renamed file)")
    if manifest["zero_byte_files"]:
        out.append(f"- {len(manifest['zero_byte_files'])} zero-byte placeholders "
                   "(AWAITING_UPLOAD, lock files, failed exports), e.g. "
                   + ", ".join(f"`{p}`" for p in manifest["zero_byte_files"][:4]))
    for ip in coverage["invalid_periods"]:
        out.append(f"- `{ip['path']}` — {ip['reason']}")
    return out


def _section_disputes(findings: dict) -> list[str]:
    disputes = findings.get("rights_disputes")
    if not disputes:
        return []
    out = ["\n### 2.4 Rights disputes & estates — cure before closing\n"]
    out.append("| Issue | Detail | Exposure |")
    out.append("|---|---|---|")
    for d in disputes:
        out.append(f"| {d['issue']} | {d['detail']} | {d['exposure']} |")
    return out


def _section_coverage(coverage: dict, findings: dict) -> list[str]:
    out = ["\n### 2.5 Statement coverage gaps — verification-blocking\n"]
    for note in findings.get("coverage_notes", []):
        out.append(f"- {note}")
    out.append("")
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
    if coverage["misfiled"]:
        out.append("\n**Misfiled statements:**\n")
        for mf in coverage["misfiled"]:
            out.append(f"- `{mf['path']}` belongs to {mf['belongs_to']}, filed under {mf['filed_under']}")
    return out


def _section_collection(requisitions: list[dict]) -> list[str]:
    out = ["\n## 4. Process to collect the missing documents\n"]
    out.append("The pipeline is the collection tracker: every received document is dropped "
               "back into the data room, the pipeline re-runs (manifest, hash-dedupe, coverage "
               "matrix, reconciliation), the 18-class scorecard re-scores automatically and "
               "this requisition log shrinks until everything is green.\n")
    out.append("| Priority | Counterparty | Request | Detail |")
    out.append("|---|---|---|---|")
    for r in requisitions:
        out.append(f"| {r['priority']} | {r['counterparty']} | {r['request']} | {r['detail']} |")
    return out


def _section_recommendation(recon: dict, findings: dict) -> list[str]:
    out = ["\n## 5. Recommendation\n"]
    rec = findings.get("recommendation", {})
    years = sorted(y for y, v in recon["by_year"].items() if v["claimed"])
    conc = recon.get("concentration") or {}
    if years:
        y = years[0]
        v = recon["by_year"][y]
        base = round(v["verified_low"] / 1000) * 1000
        conc_txt = f", ~{conc['top_song_share']:.0%} single-song concentration" if conc else ""
        out.append(f"**{rec.get('verdict', 'Do not proceed at the indicated basis.')}** "
                   f"Re-cut any offer off verified revenue (~{_money(base)} base{conc_txt}, "
                   "declining ex-sync), with closing conditions:\n")
    for c in rec.get("closing_conditions", []):
        out.append(f"- {c}")
    return out


def build_report(manifest, coverage, recon, scorecard, requisitions, claims,
                 findings: dict | None = None) -> str:
    findings = findings or {}
    out = []
    out.append(f"# {claims.get('deal_name', 'Catalog')} — Due Diligence Findings")
    out.append(f"*Automated data-room audit · seller: {claims.get('seller', 'n/a')} · "
               f"generated {date.today().isoformat()}*\n")

    out.append("## Headline\n")
    out.append(_kpi_block(manifest, coverage, recon, scorecard, claims))

    out.append("\n## 1. What is for sale\n")
    out.append(f"**Seller:** {claims.get('seller', 'n/a')} {claims.get('seller_history', '')}\n")
    out.append(f"**Offered:** {claims.get('offered', 'n/a')}\n")
    out.append(f"**Excluded:** {claims.get('excluded', 'n/a')}\n")
    cr = claims.get("claimed_revenue", {})
    if cr:
        claims_txt = " · ".join(f"FY{y} ~{_money(v)}" for y, v in sorted(cr.items()))
        if claims.get("claimed_top_song_share"):
            claims_txt += f" · top song ~{claims['claimed_top_song_share']:.0%} of revenue"
        if claims.get("claimed_top5_share"):
            claims_txt += f" · top 5 ~{claims['claimed_top5_share']:.0%}"
        out.append(f"**Seller claims:** {claims_txt}\n")

    out.append("## 2. Headline findings")
    out += _section_title_chain(findings)
    out += _section_revenue(recon)
    out += _section_fabrication(manifest, coverage)
    out += _section_disputes(findings)
    out += _section_coverage(coverage, findings)

    out.append("\n## 3. Gap analysis — fund requirements vs data room\n")
    out.append(f"**{scorecard['headline']}**\n")
    out.append("| # | Requirement | Status | Note |")
    out.append("|---|---|---|---|")
    for r in scorecard["rows"]:
        out.append(f"| {r['id']} | {r['name']} | **{r['status']}** | {r['note']} |")

    out += _section_collection(requisitions)
    out += _section_recommendation(recon, findings)
    out.append("")
    return "\n".join(out)
