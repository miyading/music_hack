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
| `pipeline/` | Extraction, manifest and coverage scripts |
| `reports/` | DD findings report (md + PDF), presentation content, KPI dashboard (html) |
| `analysis/` | Pipeline outputs: file manifest, duplicate groups |
| `data/extracted_text/` | Plain-text extraction of all 600+ PDFs |

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

*All data is fictitious — hackathon exercise material.*
