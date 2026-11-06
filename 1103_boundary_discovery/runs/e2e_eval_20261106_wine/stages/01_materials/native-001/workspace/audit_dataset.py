#!/usr/bin/env python3
"""Small reproducible audit of the downloaded UCI wine-quality tables."""
import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent

for variant in ("red", "white"):
    path = ROOT / "data" / f"winequality-{variant}.csv"
    raw = path.read_bytes()
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    fields = list(rows[0]) if rows else []
    missing = sum(value == "" for row in rows for value in row.values())
    scores = sorted({int(row["quality"]) for row in rows})
    print({
        "variant": variant,
        "rows": len(rows),
        "columns": len(fields),
        "fields": fields,
        "missing_cells": missing,
        "quality_values": scores,
        "sha256": hashlib.sha256(raw).hexdigest(),
    })
