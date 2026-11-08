#!/usr/bin/env python3
"""Fetch and analyze the frozen independent-site daily temperature replication."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests


HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)
SITE = "14092500"
NOAA = "USC00356532"
START = "2014-01-01"
END = "2023-12-31"
USGS_ROOT = "https://waterservices.usgs.gov/nwis"
NOAA_ROOT = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/all"
RNG_SEED = 20261103
BOOTSTRAPS = 2000
BLOCK_DAYS = 28


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch(name: str, url: str) -> bytes:
    response = None
    last_error = None
    for attempt in range(1, 5):
        try:
            response = requests.get(url, timeout=90)
            break
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            REQUESTS.append({
                "retrieved_at_utc": utcnow(),
                "url": url,
                "attempt": attempt,
                "status_code": None,
                "error": last_error,
            })
            time.sleep(attempt)
    if response is None:
        (HERE / f"requests_{SITE}.json").write_text(json.dumps({"requests": REQUESTS}, indent=2) + "\n")
        raise RuntimeError(f"Failed after retries: {url}: {last_error}")
    payload = response.content
    (DATA / name).write_bytes(payload)
    REQUESTS.append({
        "retrieved_at_utc": utcnow(),
        "url": response.url,
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "saved_as": f"data/{name}",
    })
    response.raise_for_status()
    time.sleep(0.2)
    return payload


def rdb_table(path: Path) -> pd.DataFrame:
    lines = path.read_text(errors="replace").splitlines()
    header_i = next(i for i, line in enumerate(lines) if line.startswith("agency_cd\t"))
    content = [lines[header_i], *lines[header_i + 2:]]
    return pd.read_csv(io.StringIO("\n".join(content)), sep="\t", dtype=str)


def parse_noaa(path: Path) -> pd.DataFrame:
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        if len(line) < 21 or line[:11] != NOAA:
            continue
        year, month, element = int(line[11:15]), int(line[15:17]), line[17:21]
        if element not in {"TMAX", "TMIN"}:
            continue
        for day in range(1, 32):
            offset = 21 + 8 * (day - 1)
            field = line[offset:offset + 8]
            if len(field) < 8:
                continue
            value = int(field[:5])
            if value == -9999:
                continue
            qflag = field[6].strip()
            if qflag:
                continue
            try:
                date = pd.Timestamp(year=year, month=month, day=day)
            except ValueError:
                continue
            rows.append({
                "date": date,
                element.lower(): value / 10.0,
                f"{element.lower()}_mflag": field[5],
                f"{element.lower()}_sflag": field[7],
            })
    long = pd.DataFrame(rows)
    if long.empty:
        raise RuntimeError("No qualified NOAA TMAX/TMIN values parsed")
    wide_values = long.pivot_table(index="date", values=["tmax", "tmin"], aggfunc="first")
    wide_flags = long.groupby("date", as_index=True).first()
    for col in ("tmax_mflag", "tmax_sflag", "tmin_mflag", "tmin_sflag"):
        if col in wide_flags:
            wide_values[col] = wide_flags[col]
    return wide_values.reset_index()


def fit_ols(train: pd.DataFrame, test: pd.DataFrame, outcome: str, with_range: bool) -> np.ndarray:
    months_train = pd.get_dummies(train["date"].dt.month, prefix="month", dtype=float)
    months_test = pd.get_dummies(test["date"].dt.month, prefix="month", dtype=float)
    months_test = months_test.reindex(columns=months_train.columns, fill_value=0.0)
    base_train = pd.DataFrame({
        "air_mean": train["air_mean"].to_numpy(),
        "log_flow": train["log_flow"].to_numpy(),
    }, index=train.index)
    base_test = pd.DataFrame({
        "air_mean": test["air_mean"].to_numpy(),
        "log_flow": test["log_flow"].to_numpy(),
    }, index=test.index)
    if with_range:
        base_train["air_range"] = train["air_range"].to_numpy()
        base_test["air_range"] = test["air_range"].to_numpy()
    x_train = np.column_stack([np.ones(len(train)), months_train.to_numpy(), base_train.to_numpy()])
    x_test = np.column_stack([np.ones(len(test)), months_test.to_numpy(), base_test.to_numpy()])
    beta, *_ = np.linalg.lstsq(x_train, train[outcome].to_numpy(dtype=float), rcond=None)
    return x_test @ beta


def mae(y: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y - pred)))


def block_bootstrap(pred: pd.DataFrame, base_col: str, full_col: str) -> dict:
    rng = np.random.default_rng(RNG_SEED)
    diffs = []
    by_year = {year: group.reset_index(drop=True) for year, group in pred.groupby(pred["date"].dt.year)}
    for _ in range(BOOTSTRAPS):
        sampled = []
        for year, group in by_year.items():
            dates = pd.DatetimeIndex(group["date"])
            n = len(group)
            if not n:
                continue
            ends = dates.searchsorted(dates + pd.Timedelta(days=BLOCK_DAYS), side="left")
            starts = np.arange(n)
            ids = []
            while len(ids) < n:
                start_idx = int(rng.integers(0, n))
                ids.extend(range(start_idx, max(start_idx + 1, int(ends[start_idx]))))
            sampled.append(group.iloc[ids[:n]])
        boot = pd.concat(sampled, ignore_index=True)
        diffs.append(mae(boot["observed"].to_numpy(), boot[base_col].to_numpy()) -
                     mae(boot["observed"].to_numpy(), boot[full_col].to_numpy()))
    values = np.asarray(diffs)
    return {
        "bootstrap_replicates": BOOTSTRAPS,
        "calendar_block_days": BLOCK_DAYS,
        "seed": RNG_SEED,
        "difference_mae_baseline_minus_amplitude_c": float(np.mean(values)),
        "ci95_percentile_c": [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))],
    }


REQUESTS: list[dict] = []


def main() -> None:
    # Metadata queries document the preselected site; no water values are read before preanalysis.
    for param in ("00010", "00060"):
        url = f"{USGS_ROOT}/site/?format=rdb&sites={SITE}&hasDataTypeCd=dv&parameterCd={param}"
        fetch(f"usgs_site_availability_{param}_{SITE}.rdb", url)
    daily_url = (f"{USGS_ROOT}/dv/?format=rdb&sites={SITE}&parameterCd=00010,00060"
                 f"&startDT={START}&endDT={END}&siteStatus=all")
    fetch(f"usgs_daily_2014_2023_{SITE}.rdb", daily_url)
    noaa_url = f"{NOAA_ROOT}/{NOAA}.dly"
    fetch(f"{NOAA}.dly", noaa_url)
    (HERE / f"requests_{SITE}.json").write_text(json.dumps({"requests": REQUESTS}, indent=2) + "\n")

    usgs = rdb_table(DATA / f"usgs_daily_2014_2023_{SITE}.rdb")
    required = {
        "water_max": "00010_00001",
        "water_min": "00010_00002",
        "water_mean": "00010_00003",
        "flow": "00060_00003",
    }
    colmap = {}
    for name, suffix in required.items():
        matches = [c for c in usgs.columns if suffix in c and not c.endswith("_cd")]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one RDB column for {name} ({suffix}), found {matches}")
        colmap[name] = matches[0]
    qualmap = {name: f"{col}_cd" for name, col in colmap.items()}
    panel = pd.DataFrame({"date": pd.to_datetime(usgs["datetime"], errors="coerce")})
    quality_counts = {}
    for name, col in colmap.items():
        panel[name] = pd.to_numeric(usgs[col], errors="coerce")
        qcol = qualmap[name]
        panel[f"{name}_qualifier"] = usgs[qcol] if qcol in usgs else ""
        ok = panel[f"{name}_qualifier"].fillna("").str.startswith("A")
        quality_counts[name] = {
            "all_nonmissing": int(panel[name].notna().sum()),
            "approved_A_prefix": int((panel[name].notna() & ok).sum()),
            "approved_estimated_Ae": int((panel[name].notna() & panel[f"{name}_qualifier"].fillna("").eq("A:e")).sum()),
            "rejected_non_A": int((panel[name].notna() & ~ok).sum()),
        }
        panel.loc[~ok, name] = np.nan

    air = parse_noaa(DATA / f"{NOAA}.dly")
    panel = panel.merge(air, on="date", how="inner", validate="one_to_one")
    panel["air_mean"] = (panel["tmax"] + panel["tmin"]) / 2
    panel["air_range"] = panel["tmax"] - panel["tmin"]
    panel["water_range"] = panel["water_max"] - panel["water_min"]
    panel["log_flow"] = np.where(panel["flow"] > 0, np.log10(panel["flow"]), np.nan)
    panel["month"] = panel["date"].dt.month
    targets = ["water_range", "water_mean", "water_max"]
    common_mask = panel[targets + ["air_mean", "air_range", "log_flow"]].notna().all(axis=1)
    common_mask &= panel["flow"] > 0
    excluded = int((~common_mask).sum())
    panel = panel.loc[common_mask].sort_values("date").reset_index(drop=True)
    panel.to_csv(HERE / "paired_daily_panel.csv", index=False)

    train = panel[panel.date.between(START, "2018-12-31")].copy()
    test = panel[panel.date.between("2019-01-01", END)].copy()
    if train.empty or test.empty:
        raise RuntimeError(f"Empty train or test: {len(train)}, {len(test)}")

    predictions = test[["date", *targets]].copy().rename(columns={t: f"observed_{t}" for t in targets})
    predictions["air_tmax"] = test["tmax"].to_numpy()
    predictions["air_tmin"] = test["tmin"].to_numpy()
    predictions["air_mean"] = test["air_mean"].to_numpy()
    predictions["air_range"] = test["air_range"].to_numpy()
    predictions["flow_cfs"] = test["flow"].to_numpy()
    metrics = {}
    for target in targets:
        base = fit_ols(train, test, target, with_range=False)
        full = fit_ols(train, test, target, with_range=True)
        bcol, fcol, ycol = f"baseline_{target}", f"with_air_range_{target}", f"observed_{target}"
        predictions[bcol] = base
        predictions[fcol] = full
        delta = mae(test[target].to_numpy(), base) - mae(test[target].to_numpy(), full)
        boot = block_bootstrap(pd.DataFrame({"date": test.date, "observed": test[target].to_numpy(),
                                             bcol: base, fcol: full}), bcol, fcol)
        metrics[target] = {
            "test_n": len(test),
            "baseline_mae_c": mae(test[target].to_numpy(), base),
            "with_air_range_mae_c": mae(test[target].to_numpy(), full),
            "difference_mae_baseline_minus_amplitude_c": delta,
            "calendar_block_uncertainty": boot,
        }
    predictions.to_csv(HERE / "daily_predictions.csv", index=False)

    result = {
        "analysis_status": "completed",
        "classification": "new_site_validation",
        "site": SITE,
        "noaa_station": NOAA,
        "data_period": [START, END],
        "train_period": [START, "2018-12-31"],
        "test_period": ["2019-01-01", END],
        "raw_usgs_rows": int(len(usgs)),
        "quality_counts": quality_counts,
        "noaa_qualified_daily_rows": int(len(air)),
        "paired_rows_after_quality_filter": int(len(panel)),
        "rows_excluded_by_common_complete_case": excluded,
        "paired_first_date": panel.date.min().date().isoformat(),
        "paired_last_date": panel.date.max().date().isoformat(),
        "train_n": int(len(train)),
        "test_n": int(len(test)),
        "noaa_nonempty_mflag_sflag_counts": {
            c: int(panel[c].fillna("").astype(str).str.strip().ne("").sum())
            for c in panel.columns if c.endswith(("_mflag", "_sflag"))
        },
        "metrics": metrics,
        "interpretation_rule": "MAE baseline minus expanded > 0 means the air daily temperature range improves prediction. The response-specificity comparisons are descriptive contrasts, not separate discoveries.",
        "requested_model": "gpt-6-luna",
        "backend_weights_verified": False,
    }
    (HERE / "analysis_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
