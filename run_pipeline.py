#!/usr/bin/env python3
"""Run the full data-room diligence pipeline.

    python3 run_pipeline.py --dataroom demo_dataroom --out output

Outputs (all regenerated on every run, so the pipeline doubles as the
collection tracker as new documents arrive):

    output/manifest.json          file inventory, duplicates, hygiene flags
    output/coverage.json          statement coverage matrix + gaps
    output/reconciliation.json    claimed vs verified revenue + bridge
    output/scorecard.json         18-class requirements scorecard
    output/requisitions.csv       prioritized requisition log
    output/dashboard.json         consolidated payload for the stakeholder UI
    output/DD_REPORT.md           stakeholder findings document
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from pipeline.manifest import build_manifest
from pipeline.coverage import build_coverage
from pipeline.reconcile import build_reconciliation
from pipeline.scorecard import build_scorecard
from pipeline.requisitions import build_requisitions
from pipeline.report import build_report
from pipeline.dashboard import build_dashboard


def main() -> None:
    ap = argparse.ArgumentParser(description="Data-room diligence pipeline")
    ap.add_argument("--dataroom", required=True, type=Path)
    ap.add_argument("--out", default=Path("output"), type=Path)
    ap.add_argument("--config", default=Path("config"), type=Path)
    args = ap.parse_args()

    cfg = args.config
    societies_cfg = json.loads((cfg / "societies.json").read_text())
    requirements = json.loads((cfg / "requirements.json").read_text())
    claims = json.loads((cfg / "claims.json").read_text())
    findings_path = cfg / "findings.json"
    findings = json.loads(findings_path.read_text()) if findings_path.exists() else {}

    args.out.mkdir(parents=True, exist_ok=True)

    print(f"[1/7] Manifest          {args.dataroom}")
    manifest = build_manifest(args.dataroom)
    print(f"      {manifest['total_files']} files · {len(manifest['duplicate_groups'])} duplicate groups · "
          f"{len(manifest['zero_byte_files'])} zero-byte · {len(manifest['future_dated'])} forward-dated")

    print("[2/7] Coverage matrix")
    coverage = build_coverage(args.dataroom, societies_cfg)
    print(f"      {coverage['overall_coverage_pct']}% coverage · "
          f"{coverage['total_missing_statements']} statements missing · "
          f"absent societies: {coverage['fully_absent_societies'] or 'none'}")

    print("[3/7] Revenue reconciliation")
    recon = build_reconciliation(args.dataroom, claims, societies_cfg)
    for y, v in sorted(recon["by_year"].items()):
        if v["claimed"]:
            print(f"      FY{y}: claimed ${v['claimed']:,.0f} -> verified "
                  f"${v['verified_low']:,.0f}-${v['verified_high']:,.0f} "
                  f"(overstated {v['overstatement_pct_low']}-{v['overstatement_pct_high']}%)")
    conc = recon.get("concentration")
    if conc:
        print(f"      top song: {conc['top_song']} = {conc['top_song_share']:.1%} "
              f"(claimed {conc['claimed_top_song_share']:.0%})")

    print("[4/7] Requirements scorecard")
    scorecard = build_scorecard(requirements, manifest, coverage)
    print(f"      {scorecard['headline']}")

    print("[5/7] Requisition log")
    requisitions = build_requisitions(scorecard, coverage)
    print(f"      {len(requisitions)} open requests")

    print("[6/7] Stakeholder findings document")
    report_md = build_report(manifest, coverage, recon, scorecard, requisitions, claims, findings)

    print("[7/7] Dashboard payload")
    dashboard = build_dashboard(manifest, coverage, recon, scorecard, requisitions, claims, findings)

    _dump(args.out / "manifest.json", manifest)
    _dump(args.out / "coverage.json", coverage)
    _dump(args.out / "reconciliation.json", recon)
    _dump(args.out / "scorecard.json", scorecard)
    with (args.out / "requisitions.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["priority", "counterparty", "request", "status", "detail"])
        w.writeheader()
        w.writerows(requisitions)
    _dump(args.out / "dashboard.json", dashboard)
    (args.out / "DD_REPORT.md").write_text(report_md)
    print(f"\nDone. Report: {args.out / 'DD_REPORT.md'} · UI payload: {args.out / 'dashboard.json'}")


def _dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str))


if __name__ == "__main__":
    main()
