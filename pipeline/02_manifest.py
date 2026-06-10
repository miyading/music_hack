#!/usr/bin/env python3
"""Build a file manifest of the data room: every file, size, md5.
Outputs manifest.csv, exact_duplicates.txt, and a junk/system file list.
Usage: ./02_manifest.py <data_room_dir> <analysis_out_dir>
"""
import os, sys, hashlib, csv, collections, re

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

rows, hashes = [], collections.defaultdict(list)
for dp, _, fn in os.walk(src):
    for f in fn:
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, src)
        try:
            sz = os.path.getsize(p)
            h = hashlib.md5(open(p, 'rb').read()).hexdigest()
        except OSError:
            sz, h = -1, ''
        rows.append((rel, os.path.splitext(f)[1].lower(), sz, h))
        if h:
            hashes[h].append(rel)

with open(f'{out}/manifest.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['path', 'ext', 'bytes', 'md5'])
    for r in sorted(rows): w.writerow(r)

dupes = [v for v in hashes.values() if len(v) > 1]
with open(f'{out}/exact_duplicates.txt', 'w') as fh:
    for grp in sorted(dupes): fh.write(' == '.join(grp) + '\n')

JUNK = r'(\.DS_Store|Thumbs\.db|^~\$|/~\$|\.tmp$|\.crdownload$)'
junk = [r[0] for r in rows if re.search(JUNK, r[0])]
empty = [r[0] for r in rows if r[2] == 0]
with open(f'{out}/hygiene.txt', 'w') as fh:
    fh.write('JUNK/SYSTEM:\n' + '\n'.join(junk))
    fh.write('\n\nZERO-BYTE:\n' + '\n'.join(empty))

print(f'files: {len(rows)} · dup groups: {len(dupes)} · junk: {len(junk)} · zero-byte: {len(empty)}')
