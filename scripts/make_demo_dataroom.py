#!/usr/bin/env python3
"""Generate a synthetic 'messy seller data room' for the Hollow Verge demo.

Reproduces the pathologies found in the real audit so the pipeline can be
demonstrated end-to-end:

  * revenue detail that sums to ~$470k for CY2023 vs an $820k seller summary
  * Capston label gross receipts (~$306k) booked as publishing revenue
  * a $42k BMW settlement double-counted across 2022 and 2023
  * a $30k PRS black-box estimate never received
  * December Rooftops at ~39% of earnings (disclosed ~30%)
  * statement gaps (GEMA 2021-23 lost, no MLC at all, scattered quarters)
  * misfiled statements (BMI in the ASCAP folder, Spotify in Amazon)
  * three byte-identical term sheets, a JPG renamed scan_final.pdf,
    zero-byte placeholders, a forward-dated Capston statement, Tidal month 13

Usage:  python3 scripts/make_demo_dataroom.py [--out demo_dataroom]
"""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path

# ---------------------------------------------------------------- catalog

ALBUMS = {
    "Soft Static (1998)": [
        "December Rooftops", "Carrying Stones", "Quiet Engine", "Paper Lanterns",
        "Salt and Circuitry", "The Long Hum", "Winter Pylon", "Glass Antenna",
        "Northern Switchboard", "Half-Light Avenue",
    ],
    "Pale Engines (2001)": [
        "Slow Engine", "Pale Engines", "Margins of the Map", "Copper Veins",
        "Static Bloom", "Night Freight", "The Quiet Mile", "Harbour Lights Off",
        "Vapour Trails East", "Low Tide Radio", "Second Skin City",
    ],
    "The Migrant Hour (2005)": [
        "The Migrant Hour", "Border Sodium", "Ash and Almanac", "Ten Cities Sleeping",
        "Wire and Water", "The Cartographer", "Open Signal", "Last Light Terminal",
        "Sleeper Routes", "Provisional Sky", "Hollow Verge",
    ],
}
SONGS = [s for album in ALBUMS.values() for s in album]
MASTER_SONGS = ALBUMS["Pale Engines (2001)"] + ALBUMS["The Migrant Hour (2005)"]

TOP_WEIGHTS = {
    "December Rooftops": 0.39,
    "Carrying Stones": 0.09,
    "Quiet Engine": 0.07,
    "Slow Engine": 0.055,
    "The Migrant Hour": 0.045,
}
_rest = (1.0 - sum(TOP_WEIGHTS.values())) / (len(SONGS) - len(TOP_WEIGHTS))
SONG_WEIGHTS = {s: TOP_WEIGHTS.get(s, _rest) for s in SONGS}

# --------------------------------------------------- statement sources

YEAR_TOTALS = {2018: 562000, 2019: 543000, 2020: 521000, 2021: 504000,
               2022: 488000, 2023: 470000, 2024: 452000, 2025: 219000}

# source -> (folder, cadence, weight, active year range)
SOURCES = {
    "PRS":     ("statements/PRS", "quarterly", 0.22, (2018, 2025)),
    "ASCAP":   ("statements/ASCAP", "quarterly", 0.17, (2018, 2025)),
    "BMI":     ("statements/BMI", "quarterly", 0.13, (2018, 2025)),
    "GEMA":    ("statements/GEMA", "half", 0.08, (2018, 2025)),
    "SACEM":   ("statements/SACEM", "half", 0.07, (2018, 2025)),
    "MCPS":    ("statements/MCPS", "quarterly", 0.06, (2018, 2025)),
    "SGAE":    ("statements/SGAE", "half", 0.03, (2018, 2025)),
    "SOCAN":   ("statements/SOCAN", "quarterly", 0.04, (2018, 2025)),
    "PPL":     ("statements/PPL", "yearly", 0.02, (2018, 2025)),
    "HFA":     ("statements/HFA", "quarterly", 0.07, (2018, 2019)),
    "Spotify": ("distributors/Spotify", "quarterly", 0.05, (2018, 2025)),
    "Apple":   ("distributors/Apple", "quarterly", 0.03, (2018, 2025)),
    "Amazon":  ("distributors/Amazon", "quarterly", 0.02, (2018, 2025)),
    "Tidal":   ("distributors/Tidal", "quarterly", 0.01, (2018, 2025)),
}

# periods that exist in reality but were never uploaded (the gaps)
GAPS = {
    "GEMA":  [f"{y}-H{h}" for y in (2021, 2022, 2023) for h in (1, 2)],
    "SACEM": ["2022-H1", "2022-H2"],
    "SGAE":  ["2019-H1", "2024-H2"],
    "PRS":   ["2023-Q2", "2024-Q3", "2025-Q1"],
    "ASCAP": ["2022-Q3", "2024-Q1"],
    "MCPS":  ["2018-Q1", "2021-Q2", "2022-Q4"],
    "BMI":   ["2020-Q2", "2023-Q1", "2024-Q2"],   # 2020-Q2 exists but misfiled
    "SOCAN": ["2019-Q3", "2023-Q3"],
    "PPL":   ["2018", "2025"],
}
MISFILED = [("BMI", "2020-Q2", "statements/ASCAP"),       # BMI quarter in ASCAP folder
            ("Spotify", "2019-Q2", "distributors/Amazon")]  # Spotify in Amazon folder

FAKE_PDF = "%PDF-1.4\n{body}\n%%EOF\n"
FAKE_JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 256 + b"\xff\xd9"


def periods_for(cadence: str, year: int) -> list[str]:
    if cadence == "quarterly":
        return [f"{year}-Q{q}" for q in range(1, 5)]
    if cadence == "half":
        return [f"{year}-H1", f"{year}-H2"]
    return [str(year)]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_pdf(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(FAKE_PDF.format(body=body))


def statement_rows(source: str, period: str, amount: float) -> list[dict]:
    return [{"song": s, "source": source, "period": period, "type": "royalty",
             "amount_usd": round(amount * w, 2)} for s, w in SONG_WEIGHTS.items()]


def build_statements(root: Path) -> None:
    for year, total in YEAR_TOTALS.items():
        # cells that actually made it into the data room this year
        cells = []
        for src, (folder, cadence, weight, (y0, y1)) in SOURCES.items():
            if not (y0 <= year <= y1):
                continue
            pers = periods_for(cadence, year)
            if year == 2025:
                pers = pers[: max(1, len(pers) // 2)]  # partial current year
            for per in pers:
                if per in GAPS.get(src, []):
                    continue
                cells.append((src, folder, per, weight / len(periods_for(cadence, year))))
        scale = total / sum(w for *_, w in cells)
        for src, folder, per, w in cells:
            amt = w * scale
            fname = f"{src}_{per}.csv" if per != str(year) else f"{src}_{year}.csv"
            write_csv(root / folder / fname, statement_rows(src, per, amt),
                      ["song", "source", "period", "type", "amount_usd"])

    # misfiled statements (present, wrong folder)
    for src, per, wrong_folder in MISFILED:
        amt = YEAR_TOTALS[int(per[:4])] * SOURCES[src][2] / 4
        write_csv(root / wrong_folder / f"{src}_{per}.csv",
                  statement_rows(src, per, amt),
                  ["song", "source", "period", "type", "amount_usd"])


def build_capston(root: Path) -> None:
    for year, gross in [(2023, 306000), (2024, 300000)]:
        per_song = gross / len(MASTER_SONGS)
        rows = [{"song": s, "source": "Capston Records", "period": str(year),
                 "type": "label_gross_receipts", "amount_usd": round(per_song, 2)}
                for s in MASTER_SONGS]
        write_csv(root / "distributors/Capston" / f"Capston_label_receipts_CY{year}.csv",
                  rows, ["song", "source", "period", "type", "amount_usd"])
    # forward-dated statement: covers Jan-Jun 2026 yet named 2H and issued Oct 2026
    write_pdf(root / "distributors/Capston/Capston_2H-FY2026.pdf",
              "CAPSTON RECORDS - ROYALTY STATEMENT\n"
              "Period: 1 January 2026 - 30 June 2026\n"
              "Statement issue date: 28 October 2026\n")


def build_summaries(root: Path) -> None:
    fy23 = [
        ("PRS performance + mechanical", "society_total", 131000),
        ("ASCAP performance", "society_total", 89000),
        ("BMI performance", "society_total", 62000),
        ("SACEM", "society_total", 34000),
        ("GEMA (estimate - statements unavailable)", "society_total", 18000),
        ("MCPS", "society_total", 27000),
        ("SGAE", "society_total", 13000),
        ("SOCAN", "society_total", 17000),
        ("PPL neighbouring rights", "society_total", 8000),
        ("US mechanical (HFA/MLC est.)", "society_total", 25000),
        ("Digital distributors", "society_total", 18000),
        ("Capston Records label receipts", "label_gross", 306000),
        ("BMW sync settlement", "settlement", 42000),
        ("PRS black-box distribution (estimated)", "accrued", 30000),
    ]
    fy24 = [
        ("PRS performance + mechanical", "society_total", 124000),
        ("ASCAP performance", "society_total", 84000),
        ("BMI performance", "society_total", 59000),
        ("SACEM", "society_total", 33000),
        ("GEMA (estimate)", "society_total", 17000),
        ("MCPS", "society_total", 25000),
        ("SGAE", "society_total", 12000),
        ("SOCAN", "society_total", 16000),
        ("PPL neighbouring rights", "society_total", 8000),
        ("US mechanical (est.)", "society_total", 24000),
        ("Digital distributors", "society_total", 19000),
        ("Capston Records label receipts", "label_gross", 300000),
        ("PRS black-box (anticipated)", "accrued", 24000),
        ("Pulse sync pipeline (anticipated)", "accrued", 40000),
    ]
    for year, items in [(2023, fy23), (2024, fy24)]:
        rows = [{"description": d, "type": t, "year": year, "amount_usd": a}
                for d, t, a in items]
        write_csv(root / "summaries" / f"seller_revenue_summary_FY{year}.csv",
                  rows, ["description", "type", "year", "amount_usd"])

    write_csv(root / "settlements/one_off_income_2022.csv",
              [{"description": "BMW sync settlement", "type": "settlement",
                "year": 2022, "amount_usd": 42000}],
              ["description", "type", "year", "amount_usd"])


def build_legal(root: Path) -> None:
    write_pdf(root / "legal/chain_of_title/1998_Vermillion_admin_copublishing_agreement.pdf",
              "ADMINISTRATION AND CO-PUBLISHING AGREEMENT (1998)\n"
              "Rights revert to the Writers upon termination.")
    write_pdf(root / "legal/chain_of_title/2017_Vermillion_Northbridge_assignment_deed_UNEXECUTED.pdf",
              "DEED OF ASSIGNMENT (2017) - recites 40 compositions\n"
              "[SIGNATURE BLOCKS BLANK] Schedule A: [SEE MASTER PURCHASE AGREEMENT]")

    masters_draft = ("ASSIGNMENT OF MASTER RECORDINGS - Reston Vance to Capston (2014)\n"
                     "DRAFT - not for execution")
    for name in ["2014_RestonVance_Capston_masters_assignment_DRAFT.pdf",
                 "masters_assignment_draft_copy2.pdf",
                 "masters_assignment_draft_copy3.pdf"]:
        write_pdf(root / "legal/masters" / name, masters_draft)

    term = "TERM SHEET - Hollow Verge Catalog\nIndicative price basis: FY23 revenue $820,000"
    for name in ["term_sheet_draft.pdf", "term_sheet_v1.pdf", "term_sheet_FINAL_post_call.pdf"]:
        write_pdf(root / "legal/term_sheet" / name, term)

    write_pdf(root / "agreements/samples/hammond_side_letter_12apr2001_fax_ILLEGIBLE.pdf",
              "[illegible fax transmission - Bug Music side letter re: 8% sample share]")
    write_pdf(root / "agreements/subpublishing/asahi_editions_subpub_2015.pdf",
              "SUB-PUBLISHING AGREEMENT - Asahi Editions (Japan), 2015")
    write_pdf(root / "agreements/subpublishing/latam_subpub_2016.pdf",
              "SUB-PUBLISHING AGREEMENT - LatAm territories, 2016")
    write_pdf(root / "agreements/sync/pulse_sync_agency_appointment_2018_UNSIGNED.pdf",
              "SYNC AGENCY APPOINTMENT - Pulse (2018, 3-year term) [unsigned]")

    write_pdf(root / "estates/petrov_bank_details_change_letter_2023.pdf",
              "Letter (by post): please redirect Julian Petrov royalties to new account.")
    write_pdf(root / "estates/akhtar_prs_suspense_notice_2022.pdf",
              "PRS notice: Lena Akhtar share held in suspense pending estate contact.")

    write_pdf(root / "correspondence/iqbal_counsel_letter_2024.pdf",
              "We act for Hassan Iqbal (12% Quiet Engine). Years of unpaid UK/US royalties.")
    write_pdf(root / "correspondence/tate_complaint_2019.pdf",
              "Second written complaint: Naomi Tate 4% share missing from PRS registration since 2005.")


def build_splits(root: Path) -> None:
    for s in SONGS:
        slug = s.lower().replace(" ", "_")
        if s == "Quiet Engine":
            write_pdf(root / "splits" / f"split_sheet_{slug}_v1.pdf",
                      "SPLIT SHEET v1 - Quiet Engine (no Iqbal share)")
            write_pdf(root / "splits" / f"split_sheet_{slug}_v2_UNSIGNED.pdf",
                      "SPLIT SHEET v2 - Quiet Engine incl. Hassan Iqbal 12% "
                      "[2 of 5 signatures missing]")
        else:
            write_pdf(root / "splits" / f"split_sheet_{slug}_signed.pdf",
                      f"SPLIT SHEET - {s} [signed]")
    # PRO registration extracts: only 2 works, one with a known mismatch
    write_csv(root / "pro_registrations/PRS_registration_extract_carrying_stones.csv",
              [{"work": "Carrying Stones", "writer": "Julian Petrov", "share_pct": 60},
               {"work": "Carrying Stones", "writer": "M. Reyes", "share_pct": 40}],
              ["work", "writer", "share_pct"])  # Naomi Tate 4% absent
    write_csv(root / "pro_registrations/PRS_registration_extract_quiet_engine.csv",
              [{"work": "Quiet Engine", "writer": "Julian Petrov", "share_pct": 55},
               {"work": "Quiet Engine", "writer": "D. Whelan", "share_pct": 45}],
              ["work", "writer", "share_pct"])  # Iqbal 12% absent


def build_junk(root: Path) -> None:
    (root / "correspondence").mkdir(parents=True, exist_ok=True)
    (root / "correspondence/scan_final.pdf").write_bytes(FAKE_JPG)  # JPG renamed

    zero = [
        "splits/AWAITING_UPLOAD_writer_agreement_petrov.pdf",
        "splits/AWAITING_UPLOAD_writer_agreement_akhtar.pdf",
        "legal/AWAITING_UPLOAD_vermillion_purchase_agreement.pdf",
        "legal/AWAITING_UPLOAD_deed_schedule_A.pdf",
        "legal/AWAITING_UPLOAD_copyright_registrations.pdf",
        "statements/PRS/PRS_2023-Q2.csv.lock",
        "statements/GEMA/GEMA_2021-H1.csv.lock",
        "statements/GEMA/GEMA_2022-H1.csv.lock",
        "statements/GEMA/GEMA_2023-H1.csv.lock",
        "summaries/export_failed_per_song_ledger.csv",
        "summaries/export_failed_recoupment_schedule.csv",
        "distributors/Atlantico/export_failed_2023-Q3.csv",
        "distributors/Tidal/Tidal_2025-13.csv",  # a 13th month, empty
    ]
    for rel in zero:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()

    # a few more byte-identical duplicates scattered around
    dup = "INTERNAL INVENTORY - 60 works (incl. excluded albums)"
    write_pdf(root / "summaries/internal_inventory_60_works.pdf", dup)
    write_pdf(root / "legal/inventory_copy.pdf", dup)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="demo_dataroom", type=Path)
    args = ap.parse_args()

    if args.out.exists():
        shutil.rmtree(args.out)
    build_statements(args.out)
    build_capston(args.out)
    build_summaries(args.out)
    build_legal(args.out)
    build_splits(args.out)
    build_junk(args.out)

    n = sum(1 for p in args.out.rglob("*") if p.is_file())
    print(f"Demo data room written to {args.out}/ ({n} files)")


if __name__ == "__main__":
    main()
