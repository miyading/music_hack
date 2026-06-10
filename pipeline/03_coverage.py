#!/usr/bin/env python3
"""Royalty statement coverage matrix: which periods exist per source, which are missing.
Handles monthly CSV folders (DSPs), quarterly PDFs (PROs), half-yearly (EU societies).
Usage: ./03_coverage.py <data_room_dir> [start_year] [end_year]
"""
import os, sys, re

src = sys.argv[1]
Y0 = int(sys.argv[2]) if len(sys.argv) > 2 else 2018
Y1 = int(sys.argv[3]) if len(sys.argv) > 3 else 2025

MONTHLY = ['Spotify', 'Deezer', 'Amazon Music', 'AppleMusic', 'Tidal']
QUARTERLY = ['APRA', 'PRS', 'SOCAN (CA)', 'MCPS', 'BMI', 'ASCAP', 'HFA mechanical']
HALF = ['SACEM', 'SGAE', 'GEMA']

def walk(folder):
    for dp, _, fn in os.walk(os.path.join(src, folder)):
        for f in fn:
            yield dp, f

for svc in MONTHLY:
    if not os.path.isdir(os.path.join(src, svc)): continue
    got = set()
    for dp, f in walk(svc):
        m = re.match(r'(\d{4})-(\d{2})\.csv$', f)
        if m: got.add((m[1], m[2]))
        m = re.match(r'(\d{2})\.csv$', f)
        if m and re.match(r'\d{4}$', os.path.basename(dp)):
            got.add((os.path.basename(dp), m[1]))
    missing = [f'{y}-{mo:02d}' for y in range(Y0, Y1+1) for mo in range(1, 13)
               if (str(y), f'{mo:02d}') not in got]
    print(f'{svc:18s} {len(got)} months · missing: {missing or "none"}')

for pro in QUARTERLY:
    if not os.path.isdir(os.path.join(src, pro)): continue
    got = set()
    for dp, f in walk(pro):
        m = re.search(r'(\d{4})[-_ ]?Q(\d)', f) or re.search(r'Q(\d)[ -_]?(\d{4})', f)
        if m:
            g = m.groups()
            got.add((g[0], g[1]) if len(g[0]) == 4 else (g[1], g[0]))
        m = re.match(r'Q(\d)\.pdf$', f)
        if m and re.match(r'\d{4}$', os.path.basename(dp)):
            got.add((os.path.basename(dp), m[1]))
    missing = [f'{y}-Q{q}' for y in range(Y0, Y1+1) for q in range(1, 5)
               if (str(y), str(q)) not in got]
    print(f'{pro:18s} {len(got)} quarters · missing: {missing or "none"}')

for soc in HALF:
    if not os.path.isdir(os.path.join(src, soc)): continue
    got = {(m[1], m[2]) for _, f in walk(soc) if (m := re.match(r'(\d{4})-H(\d)\.pdf$', f))}
    missing = [f'{y}-H{h}' for y in range(Y0, Y1+1) for h in (1, 2)
               if (str(y), str(h)) not in got]
    print(f'{soc:18s} {len(got)} halves · missing: {missing or "none"}')
