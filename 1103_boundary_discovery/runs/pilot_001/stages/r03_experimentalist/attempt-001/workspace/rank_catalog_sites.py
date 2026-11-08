#!/usr/bin/env python3
"""Use USGS time-series catalog metadata (never values) to find eligible sites."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
EXCLUDE = {"10396000", "11501000", "11502500"}
INVENTORY_PATH = Path("/Applications/ideas/1103_boundary_discovery/runs/pilot_001/stages/r00_boundary/attempt-001/workspace/data/noaa_ghcnd_inventory.txt")


def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(a))


def read_rdb(path):
    lines = path.read_text(errors="replace").splitlines()
    i = next(i for i, line in enumerate(lines) if line.startswith("agency_cd\t"))
    return pd.read_csv(pd.io.common.StringIO("\n".join([lines[i], *lines[i+2:]])), sep="\t", dtype=str)


def main():
    base = json.loads((HERE / "site_candidates.json").read_text())
    sites = [x["site_no"] for x in base["ranked_candidates"]]
    url = "https://waterservices.usgs.gov/nwis/site/?" + urlencode({
        "format": "rdb", "sites": ",".join(sites), "seriesCatalogOutput": "true"
    })
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    payload = response.content
    filename = "usgs_series_catalog_candidates.rdb"
    (DATA / filename).write_bytes(payload)
    request = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "url": response.url,
               "status_code": response.status_code, "bytes": len(payload),
               "sha256": hashlib.sha256(payload).hexdigest(), "saved_as": f"data/{filename}"}
    (HERE / "catalog_request.json").write_text(json.dumps(request, indent=2) + "\n")
    catalog = read_rdb(DATA / filename)
    site_meta = {x["site_no"]: x for x in base["ranked_candidates"]}
    needed = {("00010", "00001"), ("00010", "00002"), ("00010", "00003"), ("00060", "00003")}
    eligible = []
    diagnostics = []
    for site, meta in site_meta.items():
        rows = catalog[(catalog.site_no == site) & (catalog.data_type_cd == "dv")]
        found = set(zip(rows.parm_cd, rows.stat_cd))
        all_series = needed.issubset(found)
        date_rows = rows[rows.apply(lambda x: (x.parm_cd, x.stat_cd) in needed, axis=1)]
        periods = {}
        full_dates = all_series
        for _, row in date_rows.iterrows():
            key = f"{row.parm_cd}_{row.stat_cd}"
            periods[key] = {"begin": row.begin_date, "end": row.end_date,
                            "record_count": row.count_nu, "ts_id": row.ts_id}
            full_dates &= bool(row.begin_date <= "2014-01-01" and row.end_date >= "2023-12-31")
        rec = {"site_no": site, "all_required_series": all_series,
               "all_catalog_periods_cover_2014_2023": bool(full_dates), "series": periods}
        diagnostics.append(rec)
        if full_dates:
            eligible.append({**meta, "catalog_series": periods})
    eligible.sort(key=lambda x: (x["distance_km"], x["site_no"]))
    result = {"selection_rule": "Among active Oregon 00010 and 00060 daily-value site intersection (excluding the three prior sites), require USGS series-catalog metadata for water 00010 daily max/min/mean and flow 00060 daily mean, each spanning 2014-01-01 through 2023-12-31; match each site to its nearest eligible NOAA GHCN TMAX/TMIN station whose inventory covers the same window and is not OPHI/OCHI; choose minimum distance, tie by USGS site number.",
              "catalog_rows": int(len(catalog)), "candidate_sites_checked": len(site_meta),
              "eligible_site_count": len(eligible), "ranked_eligible_sites": eligible,
              "catalog_diagnostics": diagnostics}
    (HERE / "catalog_selection.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"catalog_rows": len(catalog), "candidate_sites_checked": len(site_meta),
                      "eligible_site_count": len(eligible), "top_candidates": eligible[:15],
                      "14139940": next((x for x in diagnostics if x["site_no"] == "14139940"), None)}, indent=2))


if __name__ == "__main__":
    main()
