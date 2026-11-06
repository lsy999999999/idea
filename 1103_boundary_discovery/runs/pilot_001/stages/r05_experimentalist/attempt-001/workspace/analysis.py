"""Reproduce the frozen 15-minute water-temperature waveform comparison."""
from __future__ import annotations

import io
import json
import math
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
RUN = HERE.parents[3]
DATA = RUN / "stages/r01_boundary/attempt-001/workspace/data"
PANEL_PATH = RUN / "parallel_exploration/paired_daily_panel.csv"
SITES = ["10396000", "11501000", "11502500"]
YEARS_TRAIN = range(2014, 2023)
TEST_YEAR = 2023
TARGETS = ["A24", "S_night", "S_day"]
SEED = 20261103
BOOTSTRAPS = 2000
BLOCK_DAYS = 28


def read_rdb(path: Path) -> pd.DataFrame:
    lines = [line for line in path.read_text(errors="replace").splitlines()
             if line and not line.startswith("#")]
    return pd.read_csv(io.StringIO("\n".join([lines[0], *lines[2:]])),
                       sep="\t", dtype=str)


def derive_days(site: str, year: int) -> list[dict]:
    path = DATA / f"iv_{site}_{year}_may_sep.rdb"
    if not path.exists():
        return []
    frame = read_rdb(path)
    valcol = next((c for c in frame.columns if c.endswith("_00010")), None)
    if valcol is None:
        raise ValueError(f"no water-temperature parameter column; columns={list(frame.columns)}")
    qcol = f"{valcol}_cd"
    frame = frame.loc[frame[qcol].fillna("").eq("A"), ["datetime", valcol]].copy()
    frame["temp"] = pd.to_numeric(frame[valcol], errors="coerce")
    frame["time"] = pd.to_datetime(frame["datetime"], format="%Y-%m-%d %H:%M",
                                   errors="coerce")
    frame = frame.dropna(subset=["temp", "time"])
    frame = frame.loc[(frame.time.dt.minute % 15 == 0)]
    frame = frame.drop_duplicates("time", keep="first").sort_values("time")
    frame["date"] = frame.time.dt.strftime("%Y-%m-%d")
    local = frame.set_index("time").temp
    out = []
    for daystr, day in frame.groupby("date", sort=True):
        day = day.sort_values("time")
        # The file timestamps are local wall time; grid membership is exact at quarter-hours.
        if len(day) < 87:
            continue
        hour = day.time.dt.hour.to_numpy() + day.time.dt.minute.to_numpy() / 60
        temp = day.temp.to_numpy(float)
        mat = np.column_stack([np.ones(len(day)), np.sin(2*np.pi*hour/24),
                               np.cos(2*np.pi*hour/24)])
        beta = np.linalg.lstsq(mat, temp, rcond=None)[0]
        peak = (math.atan2(beta[1], beta[2]) * 24 / (2*math.pi)) % 24
        d0 = pd.Timestamp(daystr)
        # Fixed elapsed-hour windows; the night interval explicitly crosses midnight.
        night_idx = (local.index >= d0 + pd.Timedelta(hours=18)) & (local.index < d0 + pd.Timedelta(days=1, hours=6))
        day_idx = (local.index >= d0 + pd.Timedelta(hours=6)) & (local.index <= d0 + pd.Timedelta(hours=18))
        night = local.loc[night_idx]
        daytime = local.loc[day_idx]
        def slope(series: pd.Series) -> float:
            if len(series) < 40:
                return float("nan")
            x = (series.index - series.index[0]).total_seconds().to_numpy() / 3600
            return float(np.linalg.lstsq(np.column_stack([np.ones(len(x)), x]),
                                         series.to_numpy(float), rcond=None)[0][1])
        out.append({
            "site": site, "date": daystr,
            "A24": float(np.hypot(beta[1], beta[2])), "phi": float(peak),
            "observed_max_hour": float(hour[np.argmax(temp)]),
            "observed_min_hour": float(hour[np.argmin(temp)]),
            "S_night": slope(night), "S_day": slope(daytime),
            "n_15min": int(len(day)),
        })
    return out


def design(frame: pd.DataFrame, expanded: bool) -> np.ndarray:
    month = pd.get_dummies(frame.month.astype(int), dtype=float)
    month = month.reindex(columns=[6, 7, 8, 9], fill_value=0.0)
    cols = [np.ones(len(frame)), *[month[c].to_numpy() for c in month.columns],
            frame.air_mean.to_numpy(float), np.log(frame.flow.to_numpy(float))]
    if expanded:
        cols.append(frame.air_range.to_numpy(float))
    return np.column_stack(cols)


def moving_block_ci(dates: pd.Series, improvement: np.ndarray) -> list[float]:
    rng = np.random.default_rng(SEED)
    order = np.argsort(pd.to_datetime(dates).to_numpy())
    vals = improvement[order]
    n = len(vals)
    if n < BLOCK_DAYS:
        return [float("nan"), float("nan")]
    means = np.empty(BOOTSTRAPS)
    nblocks = math.ceil(n / BLOCK_DAYS)
    for b in range(BOOTSTRAPS):
        starts = rng.integers(0, n, size=nblocks)
        chunks = [vals[(s + np.arange(BLOCK_DAYS)) % n] for s in starts]
        sample = np.concatenate(chunks)[:n]
        means[b] = sample.mean()
    return [float(x) for x in np.quantile(means, [0.025, 0.975])]


def retrieve_network() -> dict:
    # Follow NLDI downstream mainstem navigation from the Sprague gage.
    url = ("https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-11501000/"
           "navigation/DM/nwissite")
    record = {"url": url, "retrieved_utc_date": "2026-11-03",
              "source": "USGS NLDI, NWIS Surface Water Sites reached by downstream mainstem navigation"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "boundary-discovery-research/1.0"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read()
            record.update({"http_status": resp.status,
                           "content_type": resp.headers.get("Content-Type"),
                           "body_bytes": len(raw), "body": raw.decode("utf-8", "replace")[:500000]})
        body = json.loads(record["body"])
        ids = []
        for feat in body.get("features", []):
            props = feat.get("properties", {})
            ids.append({"identifier": props.get("identifier"), "name": props.get("name"),
                        "comid": props.get("comid"), "reachcode": props.get("reachcode"),
                        "measure": props.get("measure"), "coordinates": feat.get("geometry", {}).get("coordinates")})
        record["downstream_nwis_features"] = ids
        record["williamson_site_in_downstream_navigation"] = any(
            x.get("identifier") == "USGS-11502500" for x in ids)
        record["nearby_sprague_williamson_features"] = [
            x for x in ids if x.get("identifier") == "USGS-11502500"
            or "SPRAGUE RIVER ABOVE WILLIAMSON" in (x.get("name") or "")]
    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
    return record


def main() -> None:
    pre = json.loads((HERE / "preanalysis.json").read_text())
    daily = []
    coverage = []
    for year in [*YEARS_TRAIN, TEST_YEAR]:
        for site in SITES:
            path = DATA / f"iv_{site}_{year}_may_sep.rdb"
            if not path.exists():
                coverage.append({"site": site, "year": year, "file_exists": False,
                                 "eligible_days": 0})
                continue
            try:
                rows = derive_days(site, year)
                daily.extend(rows)
                coverage.append({"site": site, "year": year, "file_exists": True,
                                 "eligible_days": len(rows)})
            except Exception as exc:
                coverage.append({"site": site, "year": year, "file_exists": True,
                                 "eligible_days": 0,
                                 "parse_error": f"{type(exc).__name__}: {exc}"})
    water = pd.DataFrame(daily)
    panel = pd.read_csv(PANEL_PATH, dtype={"site": str})
    panel["date"] = pd.to_datetime(panel.date).dt.strftime("%Y-%m-%d")
    panel = panel.loc[panel.month.between(5, 9), ["site", "date", "month", "air_mean", "air_range", "flow"]]
    panel = panel.drop_duplicates(["site", "date"], keep="first")
    joined = water.merge(panel, on=["site", "date"], how="left", validate="one_to_one")
    joined["year"] = pd.to_datetime(joined.date).dt.year
    joined = joined.loc[joined.air_mean.notna() & joined.air_range.notna() &
                        joined.flow.notna() & (joined.flow > 0)].copy()
    joined.to_csv(HERE / "daily_diagnostics.csv", index=False)
    all_metrics = {}
    prediction_rows = []
    train_rows = joined[joined.year.isin(YEARS_TRAIN)]
    test_rows = joined[joined.year.eq(TEST_YEAR)]
    for site in SITES:
        site_train, site_test = train_rows[train_rows.site.eq(site)], test_rows[test_rows.site.eq(site)]
        all_metrics[site] = {}
        for target in TARGETS:
            tr = site_train.dropna(subset=[target])
            te = site_test.dropna(subset=[target])
            if len(tr) == 0 or len(te) == 0:
                all_metrics[site][target] = {"status": "insufficient_train_or_test_rows",
                                              "train_n": len(tr), "test_n": len(te)}
                continue
            y = tr[target].to_numpy(float)
            xb, xe = design(tr, False), design(te, False)
            xa_tr, xa_te = design(tr, True), design(te, True)
            beta_b = np.linalg.lstsq(xb, y, rcond=None)[0]
            beta_a = np.linalg.lstsq(xa_tr, y, rcond=None)[0]
            pred_b, pred_a = xe @ beta_b, xa_te @ beta_a
            obs = te[target].to_numpy(float)
            imp = np.abs(obs - pred_b) - np.abs(obs - pred_a)
            # air_range is last column in augmented matrix.
            slope = float(beta_a[-1])
            ci = moving_block_ci(te.date, imp)
            all_metrics[site][target] = {
                "train_n": int(len(tr)), "test_n": int(len(te)),
                "baseline_mae": float(np.mean(np.abs(obs-pred_b))),
                "air_range_mae": float(np.mean(np.abs(obs-pred_a))),
                "mae_improvement_baseline_minus_air_range": float(imp.mean()),
                "paired_28day_moving_block_bootstrap_95pct_ci": ci,
                "training_air_range_slope": slope,
                "training_air_range_direction": "positive" if slope > 0 else "negative" if slope < 0 else "zero",
                "model_rank_baseline": int(np.linalg.matrix_rank(xb)),
                "model_columns_baseline": int(xb.shape[1]),
                "model_rank_expanded": int(np.linalg.matrix_rank(xa_tr)),
                "model_columns_expanded": int(xa_tr.shape[1]),
            }
            for (_, row), actual, pb, pa, di in zip(te.iterrows(), obs, pred_b, pred_a, imp):
                prediction_rows.append({"site": site, "date": row.date, "target": target,
                                        "observed": actual, "baseline_prediction": pb,
                                        "air_range_prediction": pa,
                                        "absolute_error_improvement": di})
    pd.DataFrame(prediction_rows).to_csv(HERE / "heldout_predictions.csv", index=False)
    net = retrieve_network()
    (HERE / "network_check.json").write_text(json.dumps(net, indent=2) + "\n")
    network_connected = bool(net.get("williamson_site_in_downstream_navigation"))
    result = {
        "status": ("partial_primary_analysis_required_2023_site_file_unavailable"
                   if any(x.get("year") == TEST_YEAR and x.get("parse_error") for x in coverage)
                   else "completed_primary_analysis" if len(prediction_rows) else "incomplete_no_predictions"),
        "preanalysis": "preanalysis.json",
        "input_files": [str(DATA / f"iv_{site}_{year}_may_sep.rdb")
                        for year in [*YEARS_TRAIN, TEST_YEAR] for site in SITES
                        if (DATA / f"iv_{site}_{year}_may_sep.rdb").exists()] + [str(PANEL_PATH)],
        "filtering": {"water_qualifier": "exact A", "timestamp": "local datetime on exact 15-minute minute grid", "minimum_daily_values": 87,
                      "weather_flow_join": "exact site/date in paired_daily_panel.csv; finite air mean/range and positive flow",
                      "eligible_water_days_by_site_year": coverage,
                      "water_days_before_weather_flow_pairing": int(len(water)),
                      "paired_rows": int(len(joined)),
                      "train_rows_by_site": {s: int((train_rows.site == s).sum()) for s in SITES},
                      "test_rows_by_site": {s: int((test_rows.site == s).sum()) for s in SITES}},
        "models": all_metrics,
        "river_network": {"verified": network_connected,
                          "interpretation_rule": "The NLDI downstream mainstem response from 11501000 includes 11502500; this supports routed connectivity at mapped observation points, but does not establish flow travel time or flow closure.",
                          "artifact": "network_check.json"},
        "secondary_flow_ratio_model": "not_run: NLDI supports routed connectivity, but 11502500's 2023 IV file is an explicit 'No sites found' response with no temperature values; required held-out downstream response is unavailable. Do not interpret the flow ratio as a validated share or transfer predictor.",
        "2023_exposure": "2023 daily-scale water/weather analyses were previously accessed by the project (see earlier r02/r03/r04 stage outputs and parallel daily panel). This analysis froze target design before parsing the 2023 IV test rows, but the year is not new to the project.",
        "prediction_vs_mechanism": "Metrics evaluate prediction only. Conditional air_range slopes do not establish heat-exchange mechanism.",
        "requested_model": "gpt-6-luna (backend weights not verified)",
    }
    (HERE / "analysis_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "paired_rows": len(joined),
                      "models": all_metrics, "river_network": result["river_network"]}, indent=2))


if __name__ == "__main__":
    main()
