#!/usr/bin/env python3
"""Stream a CRA qualified-donees CSV and keep rows that mention challenge peer charities.

The large CRA file is intentionally not bundled. Download the current public CSV from the
URL in public_sources.json, then run:

  python backend/scripts/import_cra_peer_gifts.py path/to/qualified_donees.csv

This script is header-tolerant because CRA open-data column names can change between years.
It never guesses a gift: it outputs the raw matching row for later review/normalization.
"""
from __future__ import annotations
import argparse, csv, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"challenge_pack"/"data"

def peers():
    rows=[]
    with (DATA/"L2_peer_charities.csv").open(encoding="utf-8-sig") as fh:
        raw=[line for line in fh if not line.lstrip().startswith("#")]
    for r in csv.DictReader(raw):
        n=r.get("peer_charity","").strip()
        if n: rows.append(n)
    aliases={}
    for n in rows:
        variants={n.lower(),re.sub(r"\s*\([^)]*\)","",n).strip().lower()}
        if n.startswith("CAWST"): variants.add("cawst")
        aliases[n]=sorted(v for v in variants if v)
    return aliases

def norm(s): return re.sub(r"[^a-z0-9]+"," ",(s or "").lower()).strip()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv_path",type=Path)
    ap.add_argument("--output",type=Path,default=DATA/"cra_peer_gifts_runtime.json")
    args=ap.parse_args()
    ps=peers(); matches=[]
    with args.csv_path.open(encoding="utf-8-sig",errors="replace",newline="") as fh:
        reader=csv.DictReader(fh)
        for idx,row in enumerate(reader,2):
            hay=norm(" ".join(str(v) for v in row.values()))
            hit=[]
            for peer,als in ps.items():
                if any(norm(a) in hay for a in als if len(norm(a))>=5): hit.append(peer)
            if hit:
                matches.append({"source_row":idx,"matched_peers":hit,"raw":row})
    args.output.write_text(json.dumps(matches,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"Matched {len(matches)} CRA gift rows; wrote {args.output}")

if __name__=="__main__": main()
