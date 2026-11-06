"""Reproducible fixed-year high-frequency phase-asymmetry holdout analysis."""
from __future__ import annotations

import io
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUN = HERE.parents[3]
DATA = RUN / "stages/r01_boundary/attempt-001/workspace/data"
PANEL_PATH = RUN / "parallel_exploration/paired_daily_panel.csv"
NOAA_DIR = RUN / "stages/r00_boundary/attempt-001/workspace/data"
SITES = ["10396000", "11501000", "11502500"]
TRAIN_YEARS = range(2014, 2023)
TEST_YEAR = 2025
TARGETS = ["A24", "S_night", "S_day", "morning_valley", "afternoon_peak"]
SEED = 20261103
N_BOOT = 2000
BLOCK = 28


def read_rdb(path: Path) -> pd.DataFrame:
    lines = [line for line in path.read_text(errors="replace").splitlines()
             if line and not line.startswith("#")]
    return pd.read_csv(io.StringIO("\n".join([lines[0], *lines[2:]])), sep="\t", dtype=str)


def read_iv_days(site: str, year: int) -> tuple[list[dict], dict]:
    path = DATA / f"iv_{site}_{year}_may_sep.rdb"
    if not path.exists():
        return [], {"site": site, "year": year, "file_exists": False}
    frame = read_rdb(path)
    valcol = next((c for c in frame.columns if c.endswith("_00010")), None)
    if valcol is None:
        return [], {"site": site, "year": year, "file_exists": True,
                    "parse_error": "water-temperature 00010 column missing",
                    "columns": list(frame.columns), "raw_rows": int(len(frame))}
    qcol = f"{valcol}_cd"
    raw_rows = len(frame)
    q = frame[qcol].fillna("") if qcol in frame else pd.Series("", index=frame.index)
    temp = pd.to_numeric(frame[valcol], errors="coerce")
    times = pd.to_datetime(frame["datetime"], format="%Y-%m-%d %H:%M", errors="coerce")
    grid = times.notna() & (times.dt.minute.mod(15).eq(0)) & times.dt.second.eq(0)
    valid = q.eq("A") & temp.notna() & grid
    kept = pd.DataFrame({"time": times[valid], "temp": temp[valid]}).drop_duplicates("time").sort_values("time")
    series = kept.set_index("time")["temp"]
    rows = []
    for date, day in kept.groupby(kept.time.dt.strftime("%Y-%m-%d"), sort=True):
        day = day.sort_values("time")
        n = int(day.time.nunique())
        if n < 87:
            continue
        hour = day.time.dt.hour.to_numpy() + day.time.dt.minute.to_numpy() / 60
        y = day.temp.to_numpy(float)
        design = np.column_stack([np.ones(n), np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)])
        beta = np.linalg.lstsq(design, y, rcond=None)[0]
        d0 = pd.Timestamp(date)
        def window(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
            return series.loc[(series.index >= start) & (series.index < end)]
        night = window(d0 + pd.Timedelta(hours=18), d0 + pd.Timedelta(days=1, hours=6))
        daytime = window(d0 + pd.Timedelta(hours=6), d0 + pd.Timedelta(hours=18))
        morning = window(d0 + pd.Timedelta(hours=4), d0 + pd.Timedelta(hours=10))
        afternoon = window(d0 + pd.Timedelta(hours=12), d0 + pd.Timedelta(hours=18))
        def slope(s: pd.Series) -> float:
            if len(s) < 40:
                return float("nan")
            x = (s.index - s.index[0]).total_seconds().to_numpy() / 3600
            return float(np.linalg.lstsq(np.column_stack([np.ones(len(x)), x]), s.to_numpy(float), rcond=None)[0][1])
        rows.append({
            "site": site, "date": date, "year": year,
            "A24": float(np.hypot(beta[1], beta[2])),
            "S_night": slope(night), "S_day": slope(daytime),
            "morning_valley": float(morning.min()) if len(morning) else float("nan"),
            "afternoon_peak": float(afternoon.max()) if len(afternoon) else float("nan"),
            "n_15min": n, "night_n": int(len(night)), "day_n": int(len(daytime)),
            "morning_n": int(len(morning)), "afternoon_n": int(len(afternoon)),
        })
    audit = {"site": site, "year": year, "file_exists": True, "raw_rows": int(raw_rows),
             "a_qualifier_rows": int(q.eq("A").sum()), "valid_A_on_15min_grid": int(valid.sum()),
             "eligible_days_ge_87": len(rows), "parse_error": None}
    return rows, audit


def reproduce_covariates() -> tuple[pd.DataFrame, dict]:
    """Replay the existing panel's fixed NOAA and USGS covariate rules."""
    weather_rows = []
    noaa_audit = {}
    site_station = {"10396000": "USR0000OPHI", "11501000": "USR0000OCHI", "11502500": "USR0000OCHI"}
    for station in sorted(set(site_station.values())):
        counts = {"records": 0, "valid_values": 0, "nonblank_qflag": 0, "missing_value": 0,
                  "nonblank_mflag": 0, "nonblank_sflag": 0}
        path = NOAA_DIR / f"ghcn_{station}.dly"
        for line in path.read_text(errors="replace").splitlines():
            if len(line) < 269:
                continue
            counts["records"] += 1
            year, month, element = int(line[11:15]), int(line[15:17]), line[17:21]
            if element not in {"TMAX", "TMIN"}:
                continue
            for day in range(1, 32):
                field = line[21 + (day - 1) * 8:29 + (day - 1) * 8]
                if len(field) < 8:
                    continue
                value, mflag, qflag, sflag = int(field[:5]), field[5], field[6], field[7]
                counts["nonblank_mflag"] += bool(mflag.strip())
                counts["nonblank_qflag"] += bool(qflag.strip())
                counts["nonblank_sflag"] += bool(sflag.strip())
                if value == -9999:
                    counts["missing_value"] += 1
                    continue
                try:
                    date = pd.Timestamp(year=year, month=month, day=day)
                except ValueError:
                    continue
                counts["valid_values"] += 1
                if qflag.strip():
                    continue
                weather_rows.append((station, date, element, value / 10.0))
        noaa_audit[station] = counts
    weather = pd.DataFrame(weather_rows, columns=["station", "date", "element", "temp"])
    duplicated = int(weather.duplicated(["station", "date", "element"]).sum())
    weather = weather.pivot(index=["station", "date"], columns="element", values="temp").reset_index()
    weather["air_mean"] = (weather.TMAX + weather.TMIN) / 2
    weather["air_range"] = weather.TMAX - weather.TMIN
    usgs_path = NOAA_DIR / "usgs_daily_values_2000_to_2026.rdb"
    rows, flow_codes = [], {}
    # The existing paired panel retains rows only when all four daily USGS
    # parameters have A-prefixed qualifiers and numeric values.
    for line in usgs_path.read_text(errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if fields[0] == "agency_cd" or len(fields) < 11 or fields[1] not in site_station:
            continue
        site = fields[1]
        # Daily response repeats site-specific headers; position 9/10 is flow/code.
        try:
            values = [float(fields[i]) if fields[i] else float("nan") for i in (3, 5, 7, 9)]
            date = pd.Timestamp(fields[2])
        except (ValueError, TypeError):
            continue
        codes = [fields[i] for i in (4, 6, 8, 10)]
        code = codes[-1]
        flow_codes[(site, code)] = flow_codes.get((site, code), 0) + 1
        if all(c.startswith("A") for c in codes) and all(np.isfinite(v) for v in values):
            rows.append((site, date, values[0], values[1], values[2], values[3], code))
    daily = pd.DataFrame(rows, columns=["site", "date", "water_max", "water_min", "water_mean", "flow", "flow_cd"])
    daily = daily.merge(weather, left_on=[daily.site.map(site_station), "date"],
                        right_on=["station", "date"], how="inner", validate="many_to_one")
    # Pandas leaves a redundant join key; retain a canonical station/date panel.
    daily = daily.rename(columns={"date": "_date"})
    daily["date"] = daily["_date"]
    daily = daily[["site", "date", "flow", "flow_cd", "air_mean", "air_range"]]
    daily = daily.drop_duplicates(["site", "date"], keep="first")
    daily["year"] = daily.date.dt.year
    return daily, {"noaa_parser_counts": noaa_audit, "duplicate_weather_keys": duplicated,
                   "usgs_flow_quality_code_counts_all": {s: {q: n for (ss, q), n in flow_codes.items() if ss == s}
                                                          for s in site_station}}


def design(df: pd.DataFrame, add_range: bool) -> np.ndarray:
    month = pd.get_dummies(df.month.astype(int), dtype=float).reindex(columns=[6, 7, 8, 9], fill_value=0.)
    cols = [np.ones(len(df)), *[month[c].to_numpy() for c in month.columns],
            df.air_mean.to_numpy(float), np.log(df.flow.to_numpy(float))]
    if add_range:
        cols.append(df.air_range.to_numpy(float))
    return np.column_stack(cols)


def block_ci(dates: pd.Series, improvement: np.ndarray) -> list[float]:
    order = np.argsort(pd.to_datetime(dates).to_numpy())
    vals, n = improvement[order], len(improvement)
    if n < BLOCK:
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(SEED)
    nblocks = math.ceil(n / BLOCK)
    means = np.empty(N_BOOT)
    for i in range(N_BOOT):
        starts = rng.integers(0, n, nblocks)
        sample = np.concatenate([vals[(s + np.arange(BLOCK)) % n] for s in starts])[:n]
        means[i] = sample.mean()
    return [float(x) for x in np.quantile(means, [0.025, 0.975])]


def ghcn_audit(station: str) -> dict:
    path = NOAA_DIR / f"ghcn_{station}.dly"
    inventory = NOAA_DIR / "noaa_ghcnd_inventory.txt"
    years = set()
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            if len(line) >= 17:
                year = line[11:15]
                if year.isdigit():
                    years.add(int(year))
    inv = []
    if inventory.exists():
        for line in inventory.read_text(errors="replace").splitlines():
            if line.startswith(station) and len(line) >= 35:
                try:
                    inv.append({"element": line[31:35].strip(), "first_year": int(line[36:40]),
                                "last_year": int(line[41:45])})
                except ValueError:
                    pass
    max_inv = max([x["last_year"] for x in inv], default=None)
    return {"station": station, "file_exists": path.exists(), "years_in_dly_file": sorted(years),
            "file_max_year": max(years) if years else None, "inventory_elements": inv,
            "inventory_max_year": max_inv,
            "file_vs_inventory_year_conflict": bool(years and max_inv and max(years) > max_inv)}


def main() -> None:
    pre = json.loads((HERE / "preanalysis.json").read_text())
    daily, coverage = [], []
    for year in [*TRAIN_YEARS, TEST_YEAR]:
        for site in SITES:
            rows, audit = read_iv_days(site, year)
            daily.extend(rows)
            coverage.append(audit)
    water = pd.DataFrame(daily)
    water.to_csv(HERE / "water_daily_diagnostics.csv", index=False)
    frozen_panel = pd.read_csv(PANEL_PATH, dtype={"site": str})
    frozen_panel["date"] = pd.to_datetime(frozen_panel.date)
    frozen_panel["year"] = frozen_panel.date.dt.year
    rebuilt, covariate_audit = reproduce_covariates()
    rebuilt["month"] = rebuilt.date.dt.month
    rebuilt = rebuilt.loc[rebuilt.year.isin([*TRAIN_YEARS, TEST_YEAR]) & rebuilt.month.between(5, 9)]
    frozen_warm = frozen_panel.loc[frozen_panel.year.isin(TRAIN_YEARS) & frozen_panel.month.between(5, 9),
                                   ["site", "date", "air_mean", "air_range", "flow"]].copy()
    rebuilt_train = rebuilt.loc[rebuilt.year.isin(TRAIN_YEARS), ["site", "date", "air_mean", "air_range", "flow"]]
    verify = frozen_warm.merge(rebuilt_train,
                              on=["site", "date"], how="outer", suffixes=("_frozen", "_rebuilt"), indicator=True)
    exact_checks = {}
    for col in ["air_mean", "air_range", "flow"]:
        both = verify["_merge"].eq("both")
        exact_checks[col] = {"max_abs_difference": float((verify.loc[both, f"{col}_frozen"] - verify.loc[both, f"{col}_rebuilt"]).abs().max()) if both.any() else None,
                             "equal_rows": int(np.isclose(verify.loc[both, f"{col}_frozen"], verify.loc[both, f"{col}_rebuilt"], rtol=0, atol=1e-9).sum()) if both.any() else 0,
                             "compared_rows": int(both.sum())}
    covariate_replay = {"frozen_rows": int(len(frozen_warm)), "rebuilt_rows": int(len(rebuilt_train)),
                        "row_match_counts": {k: int(v) for k, v in verify["_merge"].value_counts().items()},
                        "additional_rebuilt_candidates_not_in_frozen_panel": int((verify["_merge"] == "right_only").sum()),
                        "numeric_checks": exact_checks,
                        "all_frozen_row_values_reproduced": bool((verify["_merge"] != "left_only").all() and all(x["max_abs_difference"] is not None and x["max_abs_difference"] <= 1e-9 for x in exact_checks.values()))}
    # Keep every training row from the frozen panel; only the predetermined 2025
    # covariates are reconstructed from the same archived source rules.
    train_panel = frozen_warm.copy()
    train_panel["month"] = train_panel.date.dt.month
    train_panel["flow_cd"] = frozen_panel.set_index(["site", "date"]).flow_cd.reindex(
        pd.MultiIndex.from_frame(train_panel[["site", "date"]])).to_numpy()
    train_panel["year"] = train_panel.date.dt.year
    test_panel = rebuilt.loc[rebuilt.year.eq(TEST_YEAR), ["site", "date", "month", "air_mean", "air_range", "flow", "flow_cd", "year"]].copy()
    panel = pd.concat([train_panel, test_panel], ignore_index=True)
    panel["date"] = pd.to_datetime(panel.date).dt.strftime("%Y-%m-%d")
    joined = water.merge(panel, on=["site", "date"], how="left", validate="one_to_one")
    joined["year"] = pd.to_datetime(joined.date).dt.year
    joined["paired_covariates"] = (joined.air_mean.notna() & joined.air_range.notna() &
                                   joined.flow.notna() & (joined.flow > 0))
    joined.to_csv(HERE / "daily_diagnostics.csv", index=False)

    panel_years = sorted(pd.to_datetime(panel.date).dt.year.unique().tolist())
    missing_panel = [y for y in [*TRAIN_YEARS, TEST_YEAR] if y not in panel_years]
    fit_results, preds = {}, []
    train, test = joined.loc[joined.year.isin(TRAIN_YEARS) & joined.paired_covariates], joined.loc[joined.year.eq(TEST_YEAR) & joined.paired_covariates]
    for site in SITES:
        fit_results[site] = {}
        for target in TARGETS:
            tr = train.loc[train.site.eq(site)].dropna(subset=[target])
            te = test.loc[test.site.eq(site)].dropna(subset=[target])
            if len(tr) == 0 or len(te) == 0:
                fit_results[site][target] = {"status": "insufficient_train_or_test_rows", "train_n": len(tr), "test_n": len(te)}
                continue
            y = tr[target].to_numpy(float)
            xb, xa = design(tr, False), design(tr, True)
            beta_b = np.linalg.lstsq(xb, y, rcond=None)[0]
            beta_a = np.linalg.lstsq(xa, y, rcond=None)[0]
            obs = te[target].to_numpy(float)
            pb, pa = design(te, False) @ beta_b, design(te, True) @ beta_a
            improvement = np.abs(obs - pb) - np.abs(obs - pa)
            # Standardize air_range and target using only the fixed training rows.
            std_beta = float(beta_a[-1] * tr.air_range.std(ddof=1) / tr[target].std(ddof=1))
            fit_results[site][target] = {
                "status": "complete", "train_n": int(len(tr)), "test_n": int(len(te)),
                "baseline_mae": float(np.mean(np.abs(obs-pb))), "air_range_mae": float(np.mean(np.abs(obs-pa))),
                "mae_improvement_baseline_minus_air_range": float(improvement.mean()),
                "paired_28day_circular_moving_block_bootstrap_95pct_ci": block_ci(te.date, improvement),
                "air_range_slope_training_units": float(beta_a[-1]),
                "air_range_standardized_slope_training_only": std_beta,
                "train_matrix_rank": int(np.linalg.matrix_rank(xa)), "train_matrix_columns": int(xa.shape[1]),
            }
            for (_, row), o, b, a, imp in zip(te.iterrows(), obs, pb, pa, improvement):
                preds.append({"site": site, "weather_station": "OPHI" if site == "10396000" else "OCHI",
                              "date": row.date, "target": target, "observed": o,
                              "baseline_prediction": b, "air_range_prediction": a,
                              "absolute_error_improvement": imp})
    pd.DataFrame(preds).to_csv(HERE / "heldout_predictions.csv", index=False)

    ghcn = [ghcn_audit("USR0000OPHI"), ghcn_audit("USR0000OCHI")]
    # Include observed panel flow quality codes and counts; no imputation or flag rewriting.
    flow_quality = {str(k): {str(q): int(v) for q, v in g.flow_cd.fillna("<missing>").value_counts().items()}
                    for k, g in joined.groupby("site")}
    any_test_site_missing = any(int((test.site == s).sum()) == 0 for s in SITES)
    summary = {
        "status": ("partial_one_site_no_2025_temperature_series" if any_test_site_missing else
                   "complete" if not missing_panel and all(x.get("file_exists") for x in coverage if x["year"] in [*TRAIN_YEARS, TEST_YEAR]) else
                   "fixed_input_failure_or_partial"),
        "protocol": pre["protocol_version"], "train_years": [*TRAIN_YEARS], "test_year": TEST_YEAR,
        "panel_years_available": panel_years, "missing_panel_years": missing_panel,
        "water_file_audit": coverage, "eligible_water_days": int(len(water)),
        "covariate_reproduction": covariate_replay, "covariate_source_audit": covariate_audit,
        "paired_rows": int(joined.paired_covariates.sum()),
        "train_paired_rows_by_site": {s: int((train.site == s).sum()) for s in SITES},
        "test_paired_rows_by_site": {s: int((test.site == s).sum()) for s in SITES},
        "flow_quality_codes_in_paired_rows": flow_quality, "noaa_ghcn_provenance": ghcn,
        "meteorological_replication_note": "10396000 uses OPHI; 11501000 and 11502500 share OCHI and are not independent weather-source replicates.",
        "models": fit_results,
        "directional_assessment": {},
        "interpretation": "Forecast errors and standardized associations are observational summaries; they do not identify heat-exchange mechanisms."
    }
    for site, targets in fit_results.items():
        sn = targets.get("S_night", {}).get("air_range_standardized_slope_training_only")
        sd = targets.get("S_day", {}).get("air_range_standardized_slope_training_only")
        mv = targets.get("morning_valley", {}).get("air_range_standardized_slope_training_only")
        ap = targets.get("afternoon_peak", {}).get("air_range_standardized_slope_training_only")
        if None not in (sn, sd, mv, ap):
            summary["directional_assessment"][site] = {
                "night_vs_day_abs_standardized_slope": abs(sn) > abs(sd),
                "valley_vs_peak_abs_standardized_slope": abs(mv) > abs(ap),
                "night_slope_negative": sn < 0, "valley_slope_negative": mv < 0,
                "day_slope_near_zero_abs_lt_0_1": abs(sd) < 0.1,
                "peak_slope_near_zero_abs_lt_0_1": abs(ap) < 0.1
            }
    (HERE / "actual_results.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": summary["status"], "panel_years": panel_years,
                      "water_days": len(water), "paired": summary["paired_rows"],
                      "train": summary["train_paired_rows_by_site"], "test": summary["test_paired_rows_by_site"],
                      "models": fit_results, "noaa": ghcn}, ensure_ascii=False))


if __name__ == "__main__":
    main()
