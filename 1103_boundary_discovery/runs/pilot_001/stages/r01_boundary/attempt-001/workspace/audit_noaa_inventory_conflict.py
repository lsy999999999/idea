#!/usr/bin/env python3
"""Compare inventory year ranges with downloaded GHCN-Daily TMAX/TMIN records."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = Path("/Applications/ideas/1103_boundary_discovery/runs/pilot_001/stages/r00_boundary/attempt-001/workspace/data")
STATIONS = ["USR0000OPHI", "USR0000OCHI"]
ELEMENTS = ["TMAX", "TMIN"]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

inventory_path = SOURCE / "noaa_ghcnd_inventory.txt"
inventory = {}
for line in inventory_path.read_text().splitlines():
    sid, lat, lon, element, first, last = line.split()[:6]
    if sid in STATIONS and element in ELEMENTS:
        inventory[(sid, element)] = {"first_year": int(first), "last_year": int(last)}

counts = {}
for sid in STATIONS:
    path = SOURCE / f"ghcn_{sid}.dly"
    for line in path.read_text(errors="replace").splitlines():
        if line[:11] != sid or line[17:21] not in ELEMENTS:
            continue
        year, month, element = int(line[11:15]), int(line[15:17]), line[17:21]
        if year not in (2024, 2025):
            continue
        rec = counts.setdefault((sid, year, element), {"valid": 0, "quality_rejected": 0})
        for day in range(1, 32):
            start = 21 + (day - 1) * 8
            value = line[start:start+5]
            qflag = line[start+6:start+7]
            if value.strip() and value != "-9999":
                if qflag.strip():
                    rec["quality_rejected"] += 1
                else:
                    rec["valid"] += 1

rows = []
for sid in STATIONS:
    for year in (2024, 2025):
        for element in ELEMENTS:
            item = counts.get((sid, year, element), {"valid": 0, "quality_rejected": 0})
            rows.append({"station_id": sid, "year": year, "element": element,
                         "inventory_last_year": inventory[(sid, element)]["last_year"],
                         "valid_dly_values_no_qflag": item["valid"],
                         "values_with_quality_flag": item["quality_rejected"],
                         "source_sha256": sha(SOURCE / f"ghcn_{sid}.dly")})

with (ROOT / "noaa_inventory_vs_dly_2024_2025.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

out = {"source_inventory": str(inventory_path), "inventory_sha256": sha(inventory_path),
       "source_dly_dir": str(SOURCE), "comparison": rows,
       "interpretation": "The inventory declares TMAX/TMIN availability only through 2023, while the downloaded .dly files contain 2024-2025 values. The existence of values in .dly does not resolve the inventory discrepancy or establish continued station operation; freeze a covariate window ending in 2023 unless NOAA metadata is independently reconciled."}
(ROOT / "noaa_inventory_conflict_audit.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(rows, ensure_ascii=False))
