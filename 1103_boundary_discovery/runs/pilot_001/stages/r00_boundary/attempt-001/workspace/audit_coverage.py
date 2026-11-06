#!/usr/bin/env python3
"""Reproducible public-source coverage audit for the three USGS seed sites."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
SITES = ["10396000", "11501000", "11502500"]
END_DATE = "2026-11-02"
BASE = "https://waterservices.usgs.gov/nwis"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BoundaryDiscoveryCoverageAudit/1.0 (public research)"})
LOG = []


def fetch(name: str, url: str, *, timeout: int = 120) -> bytes:
    requested = dt.datetime.now(dt.timezone.utc).isoformat()
    response = SESSION.get(url, timeout=timeout)
    response.raise_for_status()
    content = response.content
    path = DATA / name
    path.write_bytes(content)
    LOG.append({
        "name": name, "requested_at_utc": requested, "request_url": url,
        "response_url": response.url, "status": response.status_code,
        "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
        "headers": {k: response.headers[k] for k in ("Date", "Content-Type", "Cache-Control") if k in response.headers},
        "saved_as": f"data/{name}",
    })
    return content


def rdb_rows(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = content.decode("utf-8", errors="replace")
    lines = text.splitlines()
    h = next(i for i, line in enumerate(lines) if line.startswith("agency_cd\t"))
    reader = csv.DictReader(io.StringIO("\n".join([lines[h], *lines[h + 2:]])), delimiter="\t")
    return reader.fieldnames or [], list(reader)


def parse_day(value: str) -> dt.date:
    return dt.date.fromisoformat(value[:10])


def longest_run(days: list[dt.date]) -> int:
    if not days:
        return 0
    ordered = sorted(set(days))
    best = current = 1
    for a, b in zip(ordered, ordered[1:]):
        current = current + 1 if (b - a).days == 1 else 1
        best = max(best, current)
    return best


def summarize_daily(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out = []
    for site in SITES:
        srows = [r for r in rows if r.get("site_no") == site and r.get("datetime")]
        if not srows:
            out.append({"site_no": site, "error": "no daily rows"})
            continue
        water_cols = sorted({k for r in srows for k in r if "_00010_00003" in k and not k.endswith("_cd")})
        max_cols = sorted({k for r in srows for k in r if "_00010_00001" in k and not k.endswith("_cd")})
        flow_cols = sorted({k for r in srows for k in r if "_00060_00003" in k and not k.endswith("_cd")})
        def populated(cols: list[str], r: dict[str, str]) -> bool:
            return any(r.get(c, "").strip() not in ("", "***") for c in cols)
        water_days = [parse_day(r["datetime"]) for r in srows if populated(water_cols, r)]
        max_days = [parse_day(r["datetime"]) for r in srows if populated(max_cols, r)]
        flow_days = [parse_day(r["datetime"]) for r in srows if populated(flow_cols, r)]
        both = [parse_day(r["datetime"]) for r in srows if populated(water_cols, r) and populated(flow_cols, r)]
        years = {}
        for year in range(2000, int(END_DATE[:4]) + 1):
            start, end = dt.date(year, 1, 1), min(dt.date(year + 1, 1, 1), dt.date.fromisoformat(END_DATE) + dt.timedelta(days=1))
            exp = (end - start).days
            yrows = [r for r in srows if start <= parse_day(r["datetime"]) < end]
            w = [r for r in yrows if populated(water_cols, r)]
            q = [r for r in yrows if populated(flow_cols, r)]
            paired = [r for r in yrows if populated(water_cols, r) and populated(flow_cols, r)]
            if w or q:
                years[str(year)] = {
                    "expected_calendar_days": exp,
                    "water_mean_days": len(w), "water_max_days": sum(populated(max_cols, r) for r in yrows),
                    "flow_mean_days": len(q), "water_flow_paired_days": len(paired),
                    "water_mean_coverage_fraction": round(len(w) / exp, 4),
                    "flow_coverage_fraction": round(len(q) / exp, 4),
                    "paired_coverage_fraction": round(len(paired) / exp, 4),
                    "water_qualification_codes": sorted({r.get(c + "_cd", "") for r in w for c in water_cols if r.get(c, "").strip()}),
                }
        out.append({
            "site_no": site, "daily_rows": len(srows),
            "first_row": min(parse_day(r["datetime"]) for r in srows).isoformat(),
            "last_row": max(parse_day(r["datetime"]) for r in srows).isoformat(),
            "water_mean_first": min(water_days).isoformat() if water_days else None,
            "water_mean_last": max(water_days).isoformat() if water_days else None,
            "water_mean_days": len(set(water_days)), "water_mean_longest_daily_run": longest_run(water_days),
            "water_max_days": len(set(max_days)), "flow_mean_first": min(flow_days).isoformat() if flow_days else None,
            "flow_mean_last": max(flow_days).isoformat() if flow_days else None,
            "flow_mean_days": len(set(flow_days)), "paired_daily_days": len(set(both)), "by_year": years,
            "flow_qualification_codes": sorted({r.get(c + "_cd", "") for r in srows for c in flow_cols if r.get(c, "").strip()}),
        })
    return out


def main() -> None:
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    active_url = f"{BASE}/site/?format=rdb&stateCd=OR&parameterCd=00010&siteType=ST&siteStatus=active"
    active = fetch("usgs_active_or_temp_sites.rdb", active_url)
    active_fields, active_rows = rdb_rows(active)
    active_set = {r.get("site_no", "").strip() for r in active_rows}
    seed_in_active = [s for s in SITES if s in active_set]

    site_url = f"{BASE}/site/?format=rdb&sites={','.join(SITES)}&siteOutput=expanded"
    site_meta = fetch("usgs_seed_site_metadata.rdb", site_url)
    _, meta_rows = rdb_rows(site_meta)

    dv_url = (f"{BASE}/dv/?format=rdb&sites={','.join(SITES)}&parameterCd=00010,00060"
              f"&startDT=2000-01-01&endDT={END_DATE}&siteStatus=all")
    dv = fetch("usgs_daily_values_2000_to_2026.rdb", dv_url)
    _, dv_rows = rdb_rows(dv)
    daily = summarize_daily(dv_rows)

    iv_url = (f"{BASE}/iv/?format=rdb&sites={','.join(SITES)}&parameterCd=00010,00020"
              "&startDT=2020-01-01&endDT=2020-12-31")
    iv = fetch("usgs_iv_water_and_air_2020.rdb", iv_url)
    iv_fields, iv_rows = rdb_rows(iv)
    iv_summary = []
    for site in SITES:
        srows = [r for r in iv_rows if r.get("site_no") == site]
        series = []
        for col in iv_fields:
            if col in ("agency_cd", "site_no", "datetime") or col.endswith("_cd"):
                continue
            data = [(r.get("datetime", ""), r.get(col, "")) for r in srows if r.get(col, "").strip()]
            if data:
                parsed = []
                for ts, _ in data:
                    try:
                        parsed.append(dt.datetime.fromisoformat(ts.replace("Z", "+00:00")))
                    except ValueError:
                        pass
                diffs = [(b-a).total_seconds() for a, b in zip(parsed, parsed[1:])]
                stamps = [ts for ts, _ in data]
                series.append({
                    "column": col, "n": len(data), "first": data[0][0], "last": data[-1][0],
                    "duplicate_wallclock_timestamps": len(stamps) - len(set(stamps)),
                    "interval_seconds_counts_top5": {str(x): diffs.count(x) for x in sorted(set(diffs), key=diffs.count, reverse=True)[:5]},
                    "min_interval_seconds": min(diffs) if diffs else None,
                    "max_interval_seconds": max(diffs) if diffs else None,
                })
        iv_summary.append({"site_no": site, "returned_rows": len(srows), "nonempty_series": series})

    # NOAA GHCN-Daily inventory identifies nearby daily maximum/minimum air-temperature stations.
    inv_url = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt"
    inv = fetch("noaa_ghcnd_inventory.txt", inv_url)
    station_meta = {r["site_no"]: r for r in meta_rows}
    coords = {s: (float(station_meta[s]["dec_lat_va"]), float(station_meta[s]["dec_long_va"])) for s in SITES if s in station_meta}
    # Inventory schema: ID LAT LON ELEMENT FIRSTYEAR LASTYEAR.
    stations = {}
    for line in inv.decode("ascii", errors="ignore").splitlines():
        p = line.split()
        if len(p) != 6 or not p[0].startswith("US") or p[3] not in ("TMAX", "TMIN"):
            continue
        row = stations.setdefault(p[0], {"lat": float(p[1]), "lon": float(p[2]), "elements": {}})
        row["elements"][p[3]] = {"first_year": int(p[4]), "last_year": int(p[5])}
    def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
        lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
        dlat, dlon = lat2-lat1, lon2-lon1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 6371.0088 * 2 * math.asin(math.sqrt(h))
    nearest = {}
    for site, coord in coords.items():
        candidates = []
        for sid, rec in stations.items():
            if "TMAX" not in rec["elements"] or "TMIN" not in rec["elements"]:
                continue
            start = max(rec["elements"]["TMAX"]["first_year"], rec["elements"]["TMIN"]["first_year"])
            end = min(rec["elements"]["TMAX"]["last_year"], rec["elements"]["TMIN"]["last_year"])
            if end < 2000 or start > 2026:
                continue
            candidates.append((distance_km(coord, (rec["lat"], rec["lon"])), sid, start, end, rec))
        candidates.sort(key=lambda x: x[0])
        nearest[site] = [{"station_id": x[1], "distance_km": round(x[0], 2), "joint_inventory_years": [x[2], x[3]], "latitude": x[4]["lat"], "longitude": x[4]["lon"]} for x in candidates[:3]]
    ghcn_ids = sorted({x["station_id"] for entries in nearest.values() for x in entries[:3]})
    ghcn_series = []
    ghcn_joint_dates: dict[str, set[str]] = {}
    for sid in ghcn_ids:
        url = f"https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/{sid}.dly"
        try:
            body = fetch(f"ghcn_{sid}.dly", url)
            annual = {}
            joint_dates = set()
            for line in body.decode("ascii", errors="ignore").splitlines():
                station_id, year, month, element = line[:11].strip(), line[11:15], line[15:17], line[17:21]
                if element not in ("TMAX", "TMIN") or int(year) < 2000:
                    continue
                y = year
                annual.setdefault(y, {"TMAX": 0, "TMIN": 0, "both_days": 0, "TMAX_quality_flags": set(), "TMIN_quality_flags": set(), "days": {}})
                for day in range(1, 32):
                    offset = 21 + (day - 1) * 8
                    value, mflag, qflag, sflag = line[offset:offset+5], line[offset+5:offset+6], line[offset+6:offset+7], line[offset+7:offset+8]
                    if not value.strip() or value == "-9999" or qflag.strip():
                        continue
                    try:
                        d = dt.date(int(year), int(month), day).isoformat()
                    except ValueError:
                        continue
                    annual[y][element] += 1
                    annual[y][element + "_quality_flags"].add(qflag.strip() or "none")
                    annual[y]["days"].setdefault(d, set()).add(element)
            ghcn_joint_dates[sid] = joint_dates
            for values in annual.values():
                joint_dates.update(date for date, elements in values["days"].items() if len(elements) == 2)
                values["both_days"] = sum(len(v) == 2 for v in values["days"].values())
                del values["days"]
            ghcn_series.append({"station_id": sid, "annual": {y: {k: (sorted(v) if isinstance(v, set) else v) for k, v in d.items()} for y, d in sorted(annual.items())}})
        except Exception as exc:
            ghcn_series.append({"station_id": sid, "error": str(exc)})

    result = {
        "retrieved_at_utc": stamp,
        "selection_rule": "Start from the three USGS seed-audit sites; retain sites appearing in the live active Oregon stream-temperature station query (stateCd=OR, parameterCd=00010, siteType=ST, siteStatus=active). Do not replace or expand the set based on observed outcomes.",
        "selection": {"active_query_rows": len(active_rows), "active_unique_site_numbers": len(active_set), "seed_sites": SITES, "seed_sites_in_active_query": seed_in_active},
        "site_metadata": [{k: r.get(k) for k in ("site_no", "station_nm", "site_tp_cd", "dec_lat_va", "dec_long_va", "inventory_dt", "drain_area_va", "tz_cd", "local_time_fg")} for r in meta_rows],
        "daily_values": daily,
        "instantaneous_2020": iv_summary,
        "nearest_ghcn_daily_air_temperature_stations": nearest,
        "ghcn_daily_air_temperature_coverage": ghcn_series,
        "paired_daily_air_water_flow": {},
        "requests": LOG,
        "interpretation_boundary": "Daily-value availability does not establish 15-minute continuity or sensor/method stability. Current station metadata is not a historical station-change log. Nearest GHCN station temperatures are a spatial proxy, not on-site air temperature.",
    }
    chosen_air = {"10396000": "USR0000OPHI", "11501000": "USR0000OCHI", "11502500": "USR0000OCHI"}
    for site, air_id in chosen_air.items():
        srows = [r for r in dv_rows if r.get("site_no") == site and r.get("datetime")]
        water_cols = [k for r in srows for k in r if "_00010_00003" in k and not k.endswith("_cd")]
        flow_cols = [k for r in srows for k in r if "_00060_00003" in k and not k.endswith("_cd")]
        water_cols, flow_cols = sorted(set(water_cols)), sorted(set(flow_cols))
        matched = []
        for r in srows:
            day = r["datetime"][:10]
            has_water = any(r.get(c, "").strip() not in ("", "***") for c in water_cols)
            has_flow = any(r.get(c, "").strip() not in ("", "***") for c in flow_cols)
            if has_water and has_flow and day in ghcn_joint_dates.get(air_id, set()):
                matched.append(day)
        annual = {}
        for day in matched:
            annual[day[:4]] = annual.get(day[:4], 0) + 1
        result["paired_daily_air_water_flow"][site] = {
            "air_station_id": air_id,
            "air_station_distance_km": next(x["distance_km"] for x in nearest[site] if x["station_id"] == air_id),
            "matched_days": len(matched), "first_day": min(matched) if matched else None,
            "last_day": max(matched) if matched else None, "matched_days_by_year": annual,
        }
    (ROOT / "coverage_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selection": result["selection"], "daily_values": daily, "instantaneous_2020": iv_summary, "nearest_air": nearest, "ghcn": ghcn_series, "requests": LOG}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
