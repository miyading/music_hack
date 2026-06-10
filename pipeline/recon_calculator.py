"""Stage 8 - Revenue audit calculator: a self-contained HTML page that shows
exactly how the verified number is computed from the seller's own detail.

Left side : the seller's summary line items, with the inflating rows flagged
            (label gross receipts, double-counted settlements, accruals).
Middle    : the bridge - claimed -> deductions -> verified low -> + label
            royalty entitlement -> verified high.
Right side: the bottom-up rebuild - every society/distributor subtotal,
            expandable to the individual statement files that sum into it.

Data is embedded in the page so it opens directly from the file system
(no server needed), matching how the rest of the dashboard works.
"""

from __future__ import annotations

import json

_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revenue Audit Calculator</title>
<style>
:root{--ink:#1a1d27;--muted:#6b7280;--soft:#f1f3f9;--line:#e5e7ef;--bad:#c2402f;
      --good:#1d7a4f;--warn:#a16207;--accent:#3b4ce2;font-family:ui-sans-serif,-apple-system,'Segoe UI',Roboto,sans-serif}
body{margin:0;background:#fafbfe;color:var(--ink);font-size:14px}
header{padding:22px 28px;border-bottom:1px solid var(--line);background:#fff;
       display:flex;align-items:baseline;gap:16px;flex-wrap:wrap}
header h1{font-size:18px;margin:0}
header .sub{color:var(--muted);font-size:12px}
.tabs{display:flex;gap:6px;margin-left:auto}
.tabs button{border:1px solid var(--line);background:#fff;border-radius:10px;
             padding:6px 14px;font-weight:700;cursor:pointer;color:var(--muted)}
.tabs button.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.kpis{display:flex;gap:14px;padding:18px 28px;flex-wrap:wrap}
.kpi{background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 18px;min-width:160px}
.kpi .v{font-size:20px;font-weight:800}
.kpi .l{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.4px}
.kpi.bad .v{color:var(--bad)} .kpi.good .v{color:var(--good)}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;padding:0 28px 28px}
@media(max-width:1100px){.grid{grid-template-columns:1fr}}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden}
.card h2{font-size:13px;margin:0;padding:12px 16px;border-bottom:1px solid var(--line);
         background:var(--soft);text-transform:uppercase;letter-spacing:.4px}
.card .note{padding:10px 16px;color:var(--muted);font-size:12px;border-bottom:1px solid var(--line)}
table{width:100%;border-collapse:collapse;font-size:13px}
td,th{padding:8px 16px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr.flag td{background:#fdf2f0}
tr.total td{font-weight:800;background:var(--soft)}
.badge{display:inline-block;font-size:10px;font-weight:700;border-radius:8px;padding:2px 8px;margin-left:6px}
.badge.gross{background:#fde8e4;color:var(--bad)} .badge.dup{background:#fdf0d4;color:var(--warn)}
.badge.accr{background:#e8e4fd;color:#5b4ce2} .badge.ok{background:#e2f3e9;color:var(--good)}
.bridge td.minus{color:var(--bad)} .bridge td.plus{color:var(--good)}
details{border-bottom:1px solid var(--line)}
details summary{padding:9px 16px;cursor:pointer;display:flex;justify-content:space-between;font-weight:600}
details summary .amt{font-variant-numeric:tabular-nums}
details .files{padding:0 16px 10px;color:var(--muted);font-size:12px}
details .files div{display:flex;justify-content:space-between;padding:2px 0}
details .files code{font-size:11px}
.formula{margin:0 28px 16px;padding:14px 18px;background:#fff;border:1px dashed var(--accent);
         border-radius:14px;font-size:13px;color:var(--ink)}
.formula b{color:var(--accent)}
</style>
</head>
<body>
<header>
  <h1>Revenue Audit Calculator</h1>
  <div class="sub" id="meta"></div>
  <div class="tabs" id="tabs"></div>
</header>
<div class="kpis" id="kpis"></div>
<div class="formula" id="formula"></div>
<div class="grid">
  <div class="card"><h2>1 · Seller's summary (as claimed)</h2>
    <div class="note">The seller's own revenue summary, line by line. Highlighted rows are the inflation.</div>
    <table id="summary"></table></div>
  <div class="card"><h2>2 · The bridge (claimed &rarr; verified)</h2>
    <div class="note">Each deduction is computed from documents in the data room, not assumed.</div>
    <table class="bridge" id="bridge"></table></div>
  <div class="card"><h2>3 · Bottom-up rebuild (the actual 细账)</h2>
    <div class="note">Every statement file that sums into the verified base. Click a source to see its files.</div>
    <div id="sources"></div></div>
</div>
<script>
const DATA = __DATA__;
const fmt = x => '$' + Math.round(x).toLocaleString('en-US');
let year = DATA.years[0];

function render(){
  const Y = DATA.by_year[year], A = DATA.audit[year];
  document.getElementById('meta').textContent =
    DATA.deal + ' · seller: ' + DATA.seller + ' · generated ' + DATA.generated;
  document.getElementById('tabs').innerHTML = DATA.years.map(y =>
    `<button class="${y==year?'on':''}" onclick="year=${y};render()">FY${y}</button>`).join('');

  document.getElementById('kpis').innerHTML = `
    <div class="kpi bad"><div class="v">${fmt(Y.claimed)}</div><div class="l">Claimed FY${year}</div></div>
    <div class="kpi good"><div class="v">${fmt(Y.verified_low)}&ndash;${fmt(Y.verified_high)}</div><div class="l">Verified range</div></div>
    <div class="kpi bad"><div class="v">${Y.overstatement_pct_low}&ndash;${Y.overstatement_pct_high}%</div><div class="l">Overstated</div></div>
    <div class="kpi"><div class="v">${A.by_source.reduce((n,s)=>n+s.file_count,0)}</div><div class="l">Statement files summed</div></div>`;

  document.getElementById('formula').innerHTML =
    `<b>verified_low</b> = &Sigma; statement detail (${fmt(Y.statement_detail)}) + settlements counted once (${fmt(Y.settlements_counted_once)}) = <b>${fmt(Y.verified_low)}</b>
     &nbsp;&nbsp;|&nbsp;&nbsp; <b>verified_high</b> = verified_low + label gross ${fmt(Y.label_gross_receipts)} &times; ${Math.round(DATA.rate*100)}% royalty = <b>${fmt(Y.verified_high)}</b>
     &nbsp;&nbsp;|&nbsp;&nbsp; accrued/black-box excluded: ${fmt(Y.accrued_excluded)}`;

  const badge = t => t.includes('gross') ? '<span class="badge gross">label gross</span>'
    : t.includes('settle') ? '<span class="badge dup">double-counted</span>'
    : (t.includes('accru')||t.includes('pipeline')) ? '<span class="badge accr">never received</span>' : '';
  const rows = A.seller_summary_items.map(it => {
    const flag = badge(it.type);
    return `<tr class="${flag?'flag':''}"><td>${it.description}${flag}</td><td class="num">${fmt(it.amount)}</td></tr>`;
  }).join('');
  const sumTotal = A.seller_summary_items.reduce((n,it)=>n+it.amount,0);
  document.getElementById('summary').innerHTML = rows +
    `<tr class="total"><td>Seller total</td><td class="num">${fmt(sumTotal||Y.claimed)}</td></tr>`;

  const b = Y.bridge || {items:[],residual_unexplained:0,gap:Y.claimed-Y.verified_low};
  let bridgeRows = `<tr><td>Claimed FY${year}</td><td class="num">${fmt(Y.claimed)}</td></tr>`;
  for(const it of b.items)
    bridgeRows += `<tr><td>&minus; ${it.item}</td><td class="num minus">&minus;${fmt(it.amount)}</td></tr>`;
  bridgeRows += `<tr><td>&minus; residual (writer-share double-counting on PRO lines; per-song ledger requested)</td>
                 <td class="num minus">&minus;${fmt(b.residual_unexplained)}</td></tr>`;
  bridgeRows += `<tr class="total"><td>Verified low (rebuilt from statements)</td><td class="num">${fmt(Y.verified_low)}</td></tr>`;
  bridgeRows += `<tr><td>+ label royalty entitlement (${Math.round(DATA.rate*100)}% of gross receipts)</td>
                 <td class="num plus">+${fmt(Y.label_royalty_entitlement)}</td></tr>`;
  bridgeRows += `<tr class="total"><td>Verified high</td><td class="num">${fmt(Y.verified_high)}</td></tr>`;
  document.getElementById('bridge').innerHTML = bridgeRows;

  document.getElementById('sources').innerHTML = A.by_source.map(s => `
    <details><summary><span>${s.source} <span class="badge ok">${s.file_count} files</span></span>
      <span class="amt">${fmt(s.total)}</span></summary>
      <div class="files">${s.files.map(f =>
        `<div><code>${f.path}</code><span>${fmt(f.amount)} · ${f.rows} rows</span></div>`).join('')}</div>
    </details>`).join('') +
    (A.settlements_counted_once ? `<details><summary><span>Settlements (counted once)</span>
      <span class="amt">${fmt(A.settlements_counted_once)}</span></summary></details>` : '') +
    (A.label_gross_files.length ? `<details><summary><span>Label gross receipts (NOT publishing revenue)</span>
      <span class="amt" style="color:var(--bad)">${fmt(A.label_gross_files.reduce((n,f)=>n+f.amount,0))}</span></summary>
      <div class="files">${A.label_gross_files.map(f =>
        `<div><code>${f.path}</code><span>${fmt(f.amount)}</span></div>`).join('')}</div></details>` : '');
}
render();
</script>
</body>
</html>
"""


def build_recon_calculator(recon: dict, claims: dict, generated: str) -> str:
    years = sorted(y for y, v in recon["by_year"].items() if v["claimed"])
    payload = {
        "deal": claims.get("deal_name", "Catalog"),
        "seller": claims.get("seller", ""),
        "generated": generated,
        "rate": recon["label_royalty_rate"],
        "years": years,
        "by_year": {str(y): recon["by_year"][y] for y in years},
        "audit": {str(y): recon["audit"][y] for y in years},
    }
    # JS uses numeric keys via template strings, so re-key to plain numbers
    page = _PAGE.replace("__DATA__", json.dumps(payload))
    return page.replace("DATA.by_year[year]", "DATA.by_year[String(year)]") \
               .replace("DATA.audit[year]", "DATA.audit[String(year)]")
