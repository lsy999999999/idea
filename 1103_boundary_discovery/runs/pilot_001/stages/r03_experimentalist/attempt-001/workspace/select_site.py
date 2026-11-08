#!/usr/bin/env python3
"""Rank Oregon USGS water-temperature/flow sites using catalog metadata only."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)
BASE = "https://waterservices.usgs.gov/nwis/site/?format=rdb&stateCd=OR&siteType=ST&siteStatus=active&hasDataTypeCd=dv&parameterCd={}"
EXCLUDE = {"10396000", "11501000", "11502500"}
INV = Path("/Applications/ideas/1103_boundary_discovery/runs/pilot_001/stages/r00_boundary/attempt-001/workspace/data/noaa_ghcnd_inventory.txt")


def load_rdb(path):
    lines = path.read_text(errors="replace").splitlines()
    ix = next(i for i, line in enumerate(lines) if line.startswith("agency_cd\t"))
    return pd.read_csv(pd.io.common.StringIO("\n".join([lines[ix], *lines[ix + 2:]])), sep="\t", dtype=str)


def haversine(lat1, lon1, lat2, lon2):
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    value = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(value))


def main():
    reqs = []
    tables = {}
    for param in ("00010", "00060"):
        url = BASE.format(param)
        response = requests.get(url, timeout=90)
        response.raise_for_status()
        name = f"usgs_active_or_{param}_sites.rdb"
        (DATA / name).write_bytes(response.content)
        reqs.append({"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "url": response.url,
                     "status_code": response.status_code, "bytes": len(response.content),
                     "sha256": hashlib.sha256(response.content).hexdigest(), "saved_as": f"data/{name}"})
        tables[param] = load_rdb(DATA / name)

    inventory = {}
    for line in INV.read_text(errors="replace").splitlines():
        fields = line.split()
        if len(fields) < 6 or fields[3] not in {"TMAX", "TMIN"}:
            continue
        sid, lat, lon, element, first, last = fields[:6]
        row = inventory.setdefault(sid, {"lat": float(lat), "lon": float(lon), "years": {}})
        row["years"][element] = [int(first), int(last)]

    sites10 = tables["00010"].set_index("site_no")
    sites60 = tables["00060"].set_index("site_no")
    common = sorted((set(sites10.index) & set(sites60.index)) - EXCLUDE)
    ranked = []
    for site in common:
        row = sites10.loc[site]
        lat, lon = float(row.dec_lat_va), float(row.dec_long_va)
        candidates = []
        for station, item in inventory.items():
            if station in {"USR0000OPHI", "USR0000OCHI"}:
                continue
            tx, tn = item["years"].get("TMAX"), item["years"].get("TMIN")
            if not tx or not tn or min(tx[0], tn[0]) > 2014 or min(tx[1], tn[1]) < 2023:
                continue
            distance = haversine(lat, lon, item["lat"], item["lon"])
            candidates.append((distance, station, item))
        if candidates:
            distance, station, item = min(candidates, key=lambda x: (x[0], x[1]))
            ranked.append({"site_no": site, "station_name": row.station_nm, "latitude": lat, "longitude": lon,
                           "noaa_station": station, "noaa_latitude": item["lat"], "noaa_longitude": item["lon"],
                           "distance_km": distance, "noaa_tmax_years": item["years"]["TMAX"],
                           "noaa_tmin_years": item["years"]["TMIN"]})
    ranked.sort(key=lambda x: (x["distance_km"], x["site_no"]))
    (HERE / "selection_requests.json").write_text(json.dumps({"requests": reqs}, indent=2) + "\n")
    result = {"site_temperature_count": len(sites10), "site_flow_count": len(sites60),
              "common_eligible_site_count_before_noaa": len(common), "ranked_candidates": ranked}
    (HERE / "site_candidates.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
