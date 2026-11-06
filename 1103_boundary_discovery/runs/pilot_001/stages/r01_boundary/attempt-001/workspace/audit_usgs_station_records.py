#!/usr/bin/env python3
"""Retrieve public USGS station/time-series metadata pages for the fixed sites."""
import datetime as dt
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
SITES = ["10396000", "11501000", "11502500"]
URLS = {
    "expanded_site_metadata": "https://waterservices.usgs.gov/nwis/site/?format=rdb&sites=" + ",".join(SITES) + "&siteOutput=expanded",
    "series_catalog_metadata": "https://waterservices.usgs.gov/nwis/site/?format=rdb&sites=" + ",".join(SITES) + "&seriesCatalogOutput=true",
}
for site in SITES:
    URLS[f"station_page_{site}"] = f"https://waterdata.usgs.gov/monitoring-location/{site}/"
    URLS[f"legacy_inventory_{site}"] = f"https://waterdata.usgs.gov/nwis/inventory?agency_code=USGS&site_no={site}"

logs = []
for name, url in URLS.items():
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    request = urllib.request.Request(url, headers={"User-Agent": "BoundaryDiscoveryLab/1.0 (research audit)"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read()
            status, response_url, headers = response.status, response.geturl(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status, response_url, headers = exc.code, exc.geturl(), dict(exc.headers)
    except Exception as exc:
        logs.append({"name": name, "request_url": url, "requested_at_utc": stamp, "error": repr(exc)})
        continue
    suffix = ".rdb" if "format=rdb" in url else ".html"
    path = DATA / f"{name}{suffix}"
    path.write_bytes(body)
    text = body.decode("utf-8", "replace")
    hits = []
    for i, line in enumerate(text.splitlines()):
        if any(term in line.lower() for term in ("history", "sensor", "temperature", "thermistor", "probe", "change", "remark", "record")):
            hits.append({"line": i + 1, "text": line[:500]})
    logs.append({"name": name, "requested_at_utc": stamp, "request_url": url,
                 "response_url": response_url, "status": status, "bytes": len(body),
                 "sha256": hashlib.sha256(body).hexdigest(), "headers": headers,
                 "saved_as": "data/" + path.name, "keyword_hits": hits[:80]})

out = {"retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
       "sites": SITES,
       "interpretation_boundary": "Expanded site metadata and station pages are current/public station records, not a complete historical sensor deployment log. A page that contains no sensor/change chronology is classified as no change record located in that source, not evidence of stability.",
       "requests": logs}
(ROOT / "station_records_audit.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
print(json.dumps([{k: r.get(k) for k in ("name", "status", "bytes", "request_url", "saved_as")} for r in logs], ensure_ascii=False))
