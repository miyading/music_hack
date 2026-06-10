# Music Catalog Data-Room Diligence Pipeline

A repeatable, config-driven pipeline for auditing seller data rooms during
music catalog acquisitions. Built for the Music Moneyball Hackathon (NYC 2026)
around the Hollow Verge / Northbridge case study.

It answers, automatically and on every re-run:

1. **What is actually being sold** — and does the paper support it?
2. **What is missing, unclear, inconsistent or duplicated?**
3. **Does the claimed revenue survive a bottom-up rebuild from the seller's own statements?**
4. **What exactly do we still need, from whom, at what priority?**

No external dependencies — Python 3.10+ standard library only.

## Quick start

```bash
# 1. Generate the synthetic "messy seller data room" (381 files)
python3 scripts/make_demo_dataroom.py

# 2. Run the full pipeline against it
python3 run_pipeline.py --dataroom demo_dataroom --out output

# 3. Read the stakeholder report
open output/DD_REPORT.md
```

To run against a real data room, point `--dataroom` at the export folder and
adjust the three config files.

## Pipeline stages

```
data room ──> [1 manifest] ──> [2 coverage] ──> [3 reconcile] ──> [4 scorecard] ──> [5 requisitions] ──> [6 report]
```

| Stage | Script | What it finds |
|---|---|---|
| 1 Manifest | `pipeline/manifest.py` | MD5 hash of every file; byte-identical duplicates ("FINAL" == draft); zero-byte placeholders; extension/content mismatches (JPG renamed `.pdf`); forward-dated documents (filename periods or embedded issue dates in the future) |
| 2 Coverage | `pipeline/coverage.py` | Statement coverage matrix per society (expected cadence vs files present); exact missing periods; misfiled statements (BMI in the ASCAP folder); impossible periods (a 13th month) |
| 3 Reconcile | `pipeline/reconcile.py` | Bottom-up revenue rebuild from statement CSVs vs the seller's summary; label gross receipts booked as publishing revenue; settlements double-counted across years; accrued/black-box income never received; per-song concentration vs disclosed |
| 4 Scorecard | `pipeline/scorecard.py` | 18 required document classes scored SATISFIED / PARTIAL / MISSING; drafts and unsigned copies don't count; "executed" files byte-identical to drafts are demoted |
| 5 Requisitions | `pipeline/requisitions.py` | Every gap becomes a prioritized request addressed to the right counterparty (seller, counsel, societies, estates, BMG, Pulse) |
| 6 Report | `pipeline/report.py` | Single stakeholder-facing markdown report: KPIs, hygiene, reconciliation bridge, coverage matrix, scorecard, requisition log, recommendation |

## The pipeline is the collection tracker

Every received document is dropped back into the data room and the pipeline
re-runs; the scorecard re-scores and the requisition list shrinks until
everything is green:

```bash
cp ~/inbox/2017_assignment_deed_EXECUTED_signed.pdf demo_dataroom/legal/chain_of_title/
python3 run_pipeline.py --dataroom demo_dataroom --out output
# scorecard: 0/18 satisfied -> re-scores automatically
```

`output/requisitions.csv` doubles as the standing requisition log sent to the
seller after each run.

## Configuration (no code changes needed per deal)

| File | Contents |
|---|---|
| `config/claims.json` | The deal: seller, what's offered/excluded, the seller's claimed revenue / concentration, the label royalty rate |
| `config/societies.json` | Expected societies, statement cadence (quarterly / half-yearly / yearly) and date ranges; known distributors |
| `config/requirements.json` | The fund's 18 required document classes as filename-pattern rules with invalid patterns (draft/unsigned/illegible), minimum counts, counterparties and priorities |

## Outputs

| File | Purpose |
|---|---|
| `output/DD_REPORT.md` | Stakeholder report (the deliverable) |
| `output/manifest.json` | Full file inventory with hashes and hygiene flags |
| `output/coverage.json` | Coverage matrix with exact missing periods |
| `output/reconciliation.json` | Claimed-vs-verified bridge, per-song earnings |
| `output/scorecard.json` | 18-class gap analysis |
| `output/requisitions.csv` | Prioritized requisition log, ready to send |

## Demo headline (reproduced by the pipeline from the synthetic room)

- Claimed FY23 revenue **$820k** → verifies to **$470–525k** (overstated 56–74%)
- Bridge: **$306k** Capston label gross receipts booked as publishing (publisher keeps ~18%), **$42k** BMW settlement double-counted in 2022 *and* 2023, **$30k** PRS black-box never received
- "December Rooftops" = **39%** of earnings (disclosed ~30%); top 5 = 65% (disclosed 56%)
- Requirements: **0/18 satisfied · 8 partial · 10 missing**
- GEMA 2021–23 lost, **no MLC statements at all**, 61 statement periods missing
- Three byte-identical term sheets, a holiday photo renamed `scan_final.pdf`, 13 zero-byte placeholders, a Capston statement issue-dated in the future
