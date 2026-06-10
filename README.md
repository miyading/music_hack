# Diligence Desk

Automated due-diligence pipeline + dashboard for messy music catalog data rooms.
Built at the Standard Innovation Hackathon NYC 2026.

## The problem

Music catalog data rooms arrive messy: duplicate files, conflicting statements, missing periods,
unclear ownership, drafts labelled FINAL. Before a catalog can be valued, someone has to work out
what's actually for sale, what's been provided, what's missing, and what to chase.

## The approach

Deterministic code does the heavy lifting; LLM agents only reason over clean text.

```
data room (1,149 files)
  └─► 1. EXTRACT      pdftotext + hashing (pure code)
  └─► 2. MANIFEST     dupes, corrupt files, misfiled docs, coverage matrix (pure code)
  └─► 3. AGENTS       Rights Analyst · Financial Analyst (narrow scope, plain text only)
  └─► 4. SYNTHESIS    findings.json → dashboard, gap analysis, requisition list
```

Re-running the pipeline on an updated data room regenerates `dashboard/findings.json`;
the dashboard re-reads it — the gap analysis re-scores automatically.

## Repo layout

| Path | Contents |
|---|---|
| `dashboard/` | Front end (`index.html`) + data contract (`findings.json`) — open index.html in a browser |
| `pipeline/` | Extraction, manifest and coverage scripts (`01_extract.sh`, `02_manifest.py`, `03_coverage.py`) plus the repeatable scoring pipeline modules (see below) |
| `reports/` | DD findings report (md + PDF), presentation content, KPI dashboard (html) |
| `analysis/` | Pipeline outputs: file manifest, duplicate groups |
| `data/extracted_text/` | Plain-text extraction of all 600+ PDFs |
| `config/` + `run_pipeline.py` | Config-driven re-scoring pipeline (revenue reconciliation, 18-class scorecard, requisition log) |
| `scripts/` | Synthetic demo data-room generator for end-to-end runs |

## Dashboard

`dashboard/index.html` — persona-filtered findings (Executive / Investor / Lawyer / PRO),
severity filters, expandable finding cards with source citations, prioritised requisition queue.
Works from the file system; if served over HTTP it hot-loads `findings.json`.

## Data contract (`findings.json`)

```jsonc
{
  "meta":         { "catalog", "seller", "generated", "files_processed" },
  "kpis":         { "<persona>": [ { "label", "value", "tone", "note" } ] },
  "findings":     [ { "id", "title", "detail", "severity", "category",
                      "audiences": ["investor"|"lawyer"|"executive"|"pro"],
                      "sources": ["file.pdf"], "action" } ],
  "requisitions": [ { "counterparty", "priority": "P0|P1|P2", "items" } ]
}
```

## Repeatable scoring pipeline (`run_pipeline.py`)

Alongside the extract→agents→synthesis flow above, the repo carries a fully
deterministic, config-driven scoring pipeline (Python 3.10+ stdlib only) that
re-runs idempotently every time documents arrive — the collection tracker:

```bash
python3 scripts/make_demo_dataroom.py                       # synthetic messy data room (381 files)
python3 run_pipeline.py --dataroom demo_dataroom --out output
open output/DD_REPORT.md                                    # findings doc mirroring the deck
cat output/dashboard.json                                   # consolidated payload incl. per-party views
```

| Stage | Module | What it finds |
|---|---|---|
| Manifest | `pipeline/manifest.py` | MD5 dupes ("FINAL" == draft), zero-byte placeholders, JPGs renamed `.pdf`, forward-dated documents |
| Coverage | `pipeline/coverage.py` | Per-society coverage matrix, exact missing periods, misfiled statements, impossible periods |
| Reconcile | `pipeline/reconcile.py` | Bottom-up revenue rebuild vs claimed: label gross booked as publishing, double-counted settlements, black-box accruals, per-song concentration |
| Scorecard | `pipeline/scorecard.py` | 18 required document classes scored SATISFIED / PARTIAL / MISSING; drafts and unsigned copies don't count |
| Requisitions | `pipeline/requisitions.py` | Every gap becomes a prioritized request to the right counterparty |
| Report + Dashboard | `pipeline/report.py`, `pipeline/dashboard.py` | Stakeholder findings doc + `output/dashboard.json` UI payload |

Per-deal behaviour lives in `config/` (`claims.json` deal terms, `societies.json`
statement cadences, `requirements.json` the fund's 18-class checklist,
`findings.json` curated analyst findings) — no code changes per deal.

*All data is fictitious — hackathon exercise material.*
