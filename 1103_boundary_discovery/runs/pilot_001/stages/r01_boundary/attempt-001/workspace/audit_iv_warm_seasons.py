#!/usr/bin/env python3
"""Audit USGS instantaneous water temperature coverage in May-Sep, 2014-2025."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
SITES = ["10396000", "11501000", "11502500"]
YEARS = range(2014, 2026)
PACIFIC = ZoneInfo("America/Los_Angeles")
BASE = "https://waterservices.usgs.gov/nwis/iv/"
LOG = []


def fetch(name: str, url: str) -> tuple[bytes | None, dict]:
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    req = urllib.request.Request(url, headers={"User-Agent": "BoundaryDiscoveryLab/1.0 (research audit)"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read()
            meta = {"name": name, "requested_at_utc": stamp, "request_url": url,
                    "response_url": resp.geturl(), "status": resp.status,
                    "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                    "headers": dict(resp.headers)}
            return body, meta
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return body, {"name": name, "requested_at_utc": stamp, "request_url": url,
                      "response_url": exc.geturl(), "status": exc.code,
                      "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                      "error_body_excerpt": body[:2000].decode("utf-8", "replace")}
    except Exception as exc:
        return None, {"name": name, "requested_at_utc": stamp, "request_url": url,
                      "status": None, "error": repr(exc)}


def read_rdb(body: bytes) -> list[dict[str, str]]:
    lines = body.decode("utf-8", "replace").splitlines()
    header_idx = next((i for i, line in enumerate(lines) if line.startswith("agency_cd\t")), None)
    if header_idx is None:
        return []
    return list(csv.DictReader(lines[header_idx:], delimiter="\t"))


def parse_observations(rows: list[dict[str, str]], site: str) -> tuple[pd.DataFrame, dict]:
    temps, timestamps, ts_ids, method_ids, qualifiers = [], [], set(), set(), set()
    for row in rows:
        if row.get("site_no") != site:
            continue
        key = next((k for k in row if re.search(r"_00010$", k) and not k.endswith("_cd")), None)
        if not key:
            continue
        val = row.get(key, "").strip()
        stamp = row.get("datetime", "").strip()
        if not val or val in ("", "***") or not stamp:
            continue
        try:
            temps.append(float(val))
            timestamps.append(pd.Timestamp(stamp))
            ts_ids.add(key.rsplit("_", 1)[0])
            method_ids.add(row.get("method_cd", ""))
            qualifiers.add(row.get(key + "_cd", ""))
        except (ValueError, TypeError):
            continue
    if not timestamps:
        return pd.DataFrame(columns=["local", "utc", "value"]), {
            "n_values": 0, "ts_ids": sorted(ts_ids), "method_ids": sorted(method_ids),
            "qualifiers": sorted(qualifiers)}
    local = pd.DatetimeIndex(timestamps)
    # NWIS RDB timestamps are local wall-clock time. Infer fall-back folds from
    # the ordered series, then express elapsed intervals on the UTC timeline.
    aware = local.tz_localize("America/Los_Angeles", ambiguous="infer", nonexistent="NaT")
    df = pd.DataFrame({"local": local.astype(str), "aware": aware, "value": temps})
    df = df.dropna(subset=["aware"]).sort_values("aware")
    df["utc"] = df["aware"].dt.tz_convert("UTC")
    metadata = {"n_values": int(len(df)), "ts_ids": sorted(x for x in ts_ids if x),
                "method_ids": sorted(x for x in method_ids if x),
                "qualifiers": sorted(x for x in qualifiers if x)}
    return df[["local", "utc", "value"]], metadata


def longest_true_run(mask: list[bool]) -> int:
    best = current = 0
    for flag in mask:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def summarize(df: pd.DataFrame, site: str, year: int, meta: dict) -> dict:
    start_local = pd.Timestamp(f"{year}-05-01 00:00:00", tz="America/Los_Angeles")
    end_local = pd.Timestamp(f"{year}-10-01 00:00:00", tz="America/Los_Angeles")
    start_utc, end_utc = start_local.tz_convert("UTC"), end_local.tz_convert("UTC")
    grid = pd.date_range(start_utc, end_utc, freq="15min", inclusive="left")
    obs = df.loc[(df.utc >= start_utc) & (df.utc < end_utc), "utc"]
    counts = obs.value_counts()
    unique = pd.DatetimeIndex(counts.index).sort_values()
    on_grid = unique[unique.isin(grid)]
    present = pd.Series(0, index=grid, dtype="int8")
    present.loc[on_grid] = 1
    day_counts = present.groupby(present.index.tz_convert(PACIFIC).date).sum()
    day_good = day_counts >= 90
    missing_slots = int(len(grid) - len(on_grid))
    if len(unique) >= 2:
        diffs = unique.to_series().diff().dropna().dt.total_seconds()
        max_gap = float(max(0, diffs.max() - 900))
    else:
        max_gap = None
    return {
        "site_no": site, "year": year, "warm_season": "May 1-Sep 30 (America/Los_Angeles)",
        "http_observations": len(obs), "unique_timestamps": len(unique),
        "duplicate_timestamp_rows": int(len(obs) - len(unique)),
        "expected_15min_slots_utc": len(grid), "observed_on_grid_slots": len(on_grid),
        "missing_15min_slots": missing_slots,
        "slot_coverage_pct": round(100 * len(on_grid) / len(grid), 4),
        "days_with_ge_90_of_96_slots": int(day_good.sum()),
        "consecutive_days_ge_90_slots_max": longest_true_run(day_good.tolist()),
        "longest_elapsed_gap_seconds_minus_one_slot": max_gap,
        "first_utc": unique.min().isoformat() if len(unique) else "",
        "last_utc": unique.max().isoformat() if len(unique) else "",
        "first_local": unique.min().tz_convert(PACIFIC).isoformat() if len(unique) else "",
        "last_local": unique.max().tz_convert(PACIFIC).isoformat() if len(unique) else "",
        "ts_ids": ";".join(meta["ts_ids"]), "method_ids": ";".join(meta["method_ids"]),
        "qualifiers": ";".join(meta["qualifiers"]),
    }


def main() -> None:
    # Probe the largest requested range once to make server limits observable.
    params = {"format": "rdb", "sites": ",".join(SITES), "parameterCd": "00010",
              "startDT": "2014-05-01", "endDT": "2025-09-30"}
    url = BASE + "?" + urllib.parse.urlencode(params)
    body, meta = fetch("multi_year_probe_2014_2025", url)
    LOG.append(meta)
    if body is not None:
        (DATA / "iv_multi_year_probe.rdb").write_bytes(body)

    records = []
    for site in SITES:
        for year in YEARS:
            params = {"format": "rdb", "sites": site, "parameterCd": "00010",
                      "startDT": f"{year}-05-01", "endDT": f"{year}-09-30"}
            url = BASE + "?" + urllib.parse.urlencode(params)
            body, request_meta = fetch(f"iv_{site}_{year}_may_sep", url)
            LOG.append(request_meta)
            if body is None:
                records.append({"site_no": site, "year": year, "http_status": request_meta.get("status"),
                                "error": request_meta.get("error", "request failed")})
                continue
            rel = f"iv_{site}_{year}_may_sep.rdb"
            (DATA / rel).write_bytes(body)
            rows = read_rdb(body)
            request_meta["saved_as"] = f"data/{rel}"
            df, extra = parse_observations(rows, site)
            rec = summarize(df, site, year, extra)
            rec["http_status"] = request_meta.get("status")
            rec["response_bytes"] = request_meta.get("bytes")
            records.append(rec)
            time.sleep(0.1)

    # Current and archive station-record views: preserve response bodies and status.
    station_urls = {
        "expanded_site_metadata": "https://waterservices.usgs.gov/nwis/site/?format=rdb&sites=" + ",".join(SITES) + "&siteOutput=expanded",
        "legacy_nwis_station_records": "https://waterdata.usgs.gov/nwis/inventory?agency_code=USGS&site_no=" + SITES[0],
    }
    station_fetches = []
    for name, url in station_urls.items():
        body, rec = fetch(name, url)
        if body is not None:
            path = DATA / (name + (".rdb" if "rdb" in url else ".html"))
            path.write_bytes(body)
            rec["saved_as"] = "data/" + path.name
            rec["text_excerpt"] = body[:5000].decode("utf-8", "replace")
        station_fetches.append(rec)

    out = {"retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
           "scope": {"sites": SITES, "years": [2014, 2025],
                     "warm_season": "May 1 through September 30 inclusive in America/Los_Angeles",
                     "parameterCd": "00010 water temperature", "grid": "900 s UTC"},
           "requests": LOG, "station_record_requests": station_fetches,
           "annual_coverage": records,
           "time_handling": "RDB wall-clock timestamps localized in ordered sequence with pandas ambiguous=infer, nonexistent=NaT, then converted to UTC; expected 15-minute slot count uses actual UTC duration, so DST season boundaries and fall-back are represented correctly.",
           "interpretation_boundary": "IV availability, time-series IDs, and method codes do not establish sensor calibration or uninterrupted field deployment. Missing station-change records in queried pages are not evidence of stability."}
    (ROOT / "iv_coverage_audit.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    with (ROOT / "iv_coverage_by_site_year.csv").open("w", newline="") as f:
        fields = sorted({k for r in records for k in r})
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    print(json.dumps({"probe": LOG[0], "n_year_rows": len(records), "annual": records,
                      "station_record_requests": station_fetches}, ensure_ascii=False))


if __name__ == "__main__":
    main()
