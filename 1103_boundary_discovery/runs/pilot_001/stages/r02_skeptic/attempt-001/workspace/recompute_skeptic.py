from __future__ import annotations

import json
import io
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT = Path("/Applications/ideas/1103_boundary_discovery")
RUN = PROJECT / "runs/pilot_001"
DATA = RUN / "stages/r00_boundary/attempt-001/workspace/data"
OUT = Path(__file__).resolve().parent
SITES = {
    "10396000": ("USR0000OPHI", "DONNER UND BLITZEN"),
    "11501000": ("USR0000OCHI", "SPRAGUE"),
    "11502500": ("USR0000OCHI", "WILLIAMSON BELOW SPRAGUE"),
}
SEED = 20261103
BOOT = 600
BLOCK_DAYS = 28


def read_rdb(path: Path) -> pd.DataFrame:
    lines = [x for x in path.read_text(errors="replace").splitlines() if x and not x.startswith("#")]
    frame = pd.read_csv(io.StringIO("\n".join([lines[0], *lines[2:]])), sep="\t", dtype=str)
    # Assert semantic bindings from the service's parameter/statistic codes.
    expected = [
        "113057_00010_00001", "113058_00010_00002",
        "113059_00010_00003", "113056_00060_00003",
    ]
    actual = [x for x in frame.columns if x not in {"agency_cd", "site_no", "datetime"} and not x.endswith("_cd")]
    if actual != expected:
        raise ValueError(f"Unexpected USGS data columns: {actual}")
    frame = frame.rename(columns={
        "agency_cd": "agency", "site_no": "site", "datetime": "date",
        expected[0]: "water_max", expected[0] + "_cd": "water_max_cd",
        expected[1]: "water_min", expected[1] + "_cd": "water_min_cd",
        expected[2]: "water_mean", expected[2] + "_cd": "water_mean_cd",
        expected[3]: "flow", expected[3] + "_cd": "flow_cd",
    })
    frame["date"] = pd.to_datetime(frame.date, errors="coerce")
    for col in ["water_max", "water_min", "water_mean", "flow"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame[frame.site.isin(SITES)].copy()
    frame.attrs["rdb_header"] = lines[0]
    return frame


def read_ghcn(path: Path) -> tuple[pd.DataFrame, dict]:
    rows, counts = [], {"records": 0, "valid_values": 0, "nonblank_qflag": 0,
                        "missing_value": 0, "nonblank_mflag": 0, "nonblank_sflag": 0}
    for line in path.read_text(errors="replace").splitlines():
        if len(line) < 269:
            continue
        counts["records"] += 1
        station, year, month, element = line[:11], int(line[11:15]), int(line[15:17]), line[17:21]
        if element not in {"TMAX", "TMIN"}:
            continue
        for day in range(1, 32):
            f = line[21 + (day - 1) * 8:29 + (day - 1) * 8]
            if len(f) < 8:
                continue
            value, mflag, qflag, sflag = int(f[:5]), f[5], f[6], f[7]
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
            # Reproduce exploration.py's rule: reject nonblank qflag; retain m/s flags.
            if qflag.strip():
                continue
            rows.append((station, date, element, value / 10.0, mflag, qflag, sflag))
    wide = pd.DataFrame(rows, columns=["air_station", "date", "element", "temp_c", "mflag", "qflag", "sflag"])
    # Values are unique per station/day/element; verify before pivoting.
    duplicate_keys = int(wide.duplicated(["air_station", "date", "element"]).sum())
    wide = wide.pivot(index=["air_station", "date"], columns="element", values="temp_c").reset_index()
    counts["duplicate_station_day_element_rows"] = duplicate_keys
    return wide, counts


def build_panel() -> tuple[pd.DataFrame, dict]:
    raw = read_rdb(DATA / "usgs_daily_values_2000_to_2026.rdb")
    air_parts, quality = [], {}
    for site, (station, _) in SITES.items():
        air, q = read_ghcn(DATA / f"ghcn_{station}.dly")
        quality[station] = q
        air = air[air.air_station.eq(station)].copy()
        air["air_mean"] = (air.TMAX + air.TMIN) / 2
        air["air_range"] = air.TMAX - air.TMIN
        air["site"] = site
        air_parts.append(air[["site", "date", "air_mean", "air_range"]])
    air = pd.concat(air_parts, ignore_index=True)
    panel = raw.merge(air, on=["site", "date"], how="inner", validate="one_to_one")
    panel = panel[panel.date.dt.year.between(2014, 2024)].copy()
    panel["year"] = panel.date.dt.year
    panel["month"] = panel.date.dt.month.astype(str)
    panel["water_range"] = panel.water_max - panel.water_min
    panel["log_flow"] = np.log10(panel.flow.clip(lower=0) + 0.1)
    panel["low_flow"] = 0
    cutoffs = {}
    for site, group in panel[panel.year.between(2014, 2019)].groupby("site"):
        cut = float(group.log_flow.quantile(.25))
        cutoffs[site] = cut
        panel.loc[panel.site.eq(site), "low_flow"] = (panel.loc[panel.site.eq(site), "log_flow"] <= cut).astype(int)
    panel["air_range_x_low_flow"] = panel.air_range * panel.low_flow
    good = (
        panel.water_max_cd.fillna("").str.startswith("A") &
        panel.water_min_cd.fillna("").str.startswith("A") &
        panel.water_mean_cd.fillna("").str.startswith("A") &
        panel.flow_cd.fillna("").str.startswith("A")
    )
    panel = panel[good & panel[["water_max", "water_min", "water_mean", "flow", "air_mean", "air_range"]].notna().all(axis=1)].copy()
    return panel, {"ghcn_parser_counts": quality, "low_flow_cutoffs_log10_cfs": cutoffs,
                   "flow_qualifier_counts": panel.flow_cd.value_counts().to_dict()}


def fit_predict(train: pd.DataFrame, test: pd.DataFrame, target: str, features: list[str], site_holdout=False) -> np.ndarray:
    cats = ["month"] if site_holdout else ["site", "month"]
    prep = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), cats),
        ("num", StandardScaler(), features),
    ])
    model = make_pipeline(prep, LinearRegression())
    model.fit(train[cats + features], train[target])
    return model.predict(test[cats + features])


def summary(y, pred):
    return {"n_rows": int(len(y)), "mae_c": float(mean_absolute_error(y, pred)),
            "rmse_c": float(mean_squared_error(y, pred) ** .5), "r2": float(r2_score(y, pred))}


def sampled_date_weights(df: pd.DataFrame, rng: np.random.Generator, block_days=BLOCK_DAYS) -> pd.Series:
    # Sample dates in contiguous blocks within year, jointly for all sites.
    counts = {}
    for year, g in df.groupby("year"):
        dates = np.array(sorted(g.date.unique()), dtype="datetime64[ns]")
        if not len(dates):
            continue
        nblocks = int(np.ceil(len(dates) / block_days))
        picked = []
        for _ in range(nblocks):
            start = int(rng.integers(0, len(dates)))
            picked.extend(dates[(start + np.arange(block_days)) % len(dates)])
        vals, nums = np.unique(np.asarray(picked), return_counts=True)
        counts.update({pd.Timestamp(d): int(n) for d, n in zip(vals, nums)})
    return pd.Series(counts, dtype=float)


def block_ci_for_mae_diffs(test, predictions, targets, reps=BOOT):
    rng = np.random.default_rng(SEED)
    out = {}
    for target, predset in predictions.items():
        y = test[target].to_numpy()
        out[target] = {}
        for name, pred in predset.items():
            errs = np.abs(y - pred)
            out[target][name] = float(errs.mean())
        base_name, air_name, inter_name = "base", "air", "interaction"
        diffs = {k: [] for k in ["base_minus_air", "air_minus_interaction", "base_minus_interaction"]}
        err_map = pd.DataFrame({"site": test.site, "date": test.date,
                                "base": np.abs(y - predset[base_name]),
                                "air": np.abs(y - predset[air_name]),
                                "interaction": np.abs(y - predset[inter_name])})
        date_errors = err_map.groupby("date")[["base", "air", "interaction"]].sum()
        date_counts = err_map.groupby("date").size()
        # Bootstrap by calendar date blocks, so the duplicated NOAA proxy is sampled once per date.
        for _ in range(reps):
            weights = sampled_date_weights(test, rng)
            dates = weights.index.intersection(date_errors.index)
            w = weights.loc[dates].to_numpy()
            denom = float((w * date_counts.loc[dates].to_numpy()).sum())
            vals = (date_errors.loc[dates].to_numpy() * w[:, None]).sum(axis=0) / denom
            m = pd.Series(vals, index=["base", "air", "interaction"])
            diffs["base_minus_air"].append(m.base - m.air)
            diffs["air_minus_interaction"].append(m.air - m.interaction)
            diffs["base_minus_interaction"].append(m.base - m.interaction)
        for key, vals in diffs.items():
            out[target][key] = {"mean_c": float(np.mean(vals)), "ci95_c": [float(x) for x in np.quantile(vals, [.025, .975])],
                                "prob_improvement_positive": float(np.mean(np.array(vals) > 0)),
                                "block_days": BLOCK_DAYS, "bootstrap_reps": reps}
    return out


def interaction_block_bootstrap(train: pd.DataFrame, reps=BOOT):
    # Frisch-Waugh equivalent via least squares with explicit site/month controls.
    rng = np.random.default_rng(SEED + 1)
    cols = ["air_mean", "log_flow", "air_range", "air_range_x_low_flow"]
    xcat = pd.get_dummies(train[["site", "month"]], drop_first=True, dtype=float)
    y = train.water_range.to_numpy()
    def coefs(df, weights=None):
        cats = pd.get_dummies(df[["site", "month"]], drop_first=True, dtype=float)
        xx = np.column_stack([np.ones(len(df)), cats.to_numpy(), df[cols].to_numpy()])
        yy = df.water_range.to_numpy()
        if weights is not None:
            sw = np.sqrt(weights)
            xx, yy = xx * sw[:, None], yy * sw
        return np.linalg.lstsq(xx, yy, rcond=None)[0][-4:]
    point = coefs(train)
    samples = []
    for _ in range(reps):
        date_weights = sampled_date_weights(train, rng)
        weights = train.date.map(date_weights).fillna(0).to_numpy()
        samples.append(coefs(train, weights))
    a = np.asarray(samples)
    return {
        "fit_rows": int(len(train)), "block_days": BLOCK_DAYS, "bootstrap_reps": reps,
        "coefficients": {name: {"estimate_c_per_c": float(point[i]), "ci95_c_per_c": [float(x) for x in np.quantile(a[:, i], [.025, .975])],
                                "prob_positive": float(np.mean(a[:, i] > 0))}
                         for i, name in enumerate(["air_mean", "log_flow", "air_range", "air_range_x_low_flow"])},
        "derived_slopes": {
            "air_range_slope_normal_flow": {"estimate": float(point[2]), "ci95": [float(x) for x in np.quantile(a[:, 2], [.025, .975])]},
            "air_range_slope_low_flow": {"estimate": float(point[2] + point[3]), "ci95": [float(x) for x in np.quantile(a[:, 2] + a[:, 3], [.025, .975])]},
            "low_flow_increment": {"estimate": float(point[3]), "ci95": [float(x) for x in np.quantile(a[:, 3], [.025, .975])]},
        },
    }


def main():
    panel, parser = build_panel()
    train = panel[panel.year.between(2014, 2019)].copy()
    test = panel[panel.year.between(2020, 2024)].copy()
    targets = {"water_range": "water_range", "water_mean": "water_mean", "water_max": "water_max"}
    predictions, point = {}, {}
    features = {"base": ["air_mean", "log_flow"],
                "air": ["air_mean", "log_flow", "air_range"],
                "interaction": ["air_mean", "log_flow", "air_range", "air_range_x_low_flow"]}
    for label, target in targets.items():
        predictions[label] = {}
        point[label] = {}
        for model_name, cols in features.items():
            pred = fit_predict(train, test, target, cols)
            predictions[label][model_name] = pred
            point[label][model_name] = summary(test[target].to_numpy(), pred)
    block = block_ci_for_mae_diffs(test, predictions, targets)

    leave_site = {}
    for held in SITES:
        tr = panel[panel.site.ne(held) & panel.year.between(2014, 2019)]
        te = panel[panel.site.eq(held) & panel.year.between(2020, 2024)]
        leave_site[held] = {"held_site": SITES[held][1], "n_train_sites": int(tr.site.nunique()),
                            "test_rows": int(len(te)), "test_years": [2020, 2024], "metrics": {}}
        for model_name in ["base", "air"]:
            cols = features[model_name]
            pr = fit_predict(tr, te, "water_range", cols, site_holdout=True)
            leave_site[held]["metrics"][model_name] = summary(te.water_range.to_numpy(), pr)

    out = {
        "classification": "对已查看数据的探索性独立复核；非确认性测试。",
        "data_and_parsing": {"paired_approved_rows": int(len(panel)), "train_rows": int(len(train)), "test_rows": int(len(test)),
                             "rows_by_site": panel.groupby("site").size().to_dict(),
                             "rows_by_site_year": {f"{s}_{int(y)}": int(n) for (s,y),n in panel.groupby(["site","year"]).size().items()},
                             "rdb_semantic_mapping": {"113057_00010_00001":"water daily max (deg C)","113058_00010_00002":"water daily min (deg C)","113059_00010_00003":"water daily mean (deg C)","113056_00060_00003":"discharge daily mean (cfs)"},
                             "rdb_quality_rule": "水温 max/min/mean 与流量限定符以 A 开头；保留 A:e，排除 P。",
                             "ghcn_quality_rule": "数值非 -9999 且 qflag 为空；符合 exploration.py，但 mflag/sflag 不筛除。",
                             "ghcn_parser_counts": parser["ghcn_parser_counts"],
                             "air_station_reuse": {"USR0000OPHI": ["10396000"], "USR0000OCHI": ["11501000", "11502500"]},
                             "low_flow_cutoffs_log10_cfs": parser["low_flow_cutoffs_log10_cfs"],
                             "flow_qualifier_counts": parser["flow_qualifier_counts"]},
        "time_holdout_point_metrics": {k: {m:v for m,v in models.items()} for k,models in point.items()},
        "time_holdout_mae_difference_calendar_block_bootstrap": block,
        "training_interaction_calendar_block_bootstrap": interaction_block_bootstrap(train),
        "leave_site_out_range_2020_2024": leave_site,
        "effective_independence_notes": {"daily_rows": int(len(test)), "test_calendar_dates": int(test.date.nunique()),
                                         "unique_air_stations": 2, "sites_using_same_air_station": 2,
                                         "consecutive_day_pairs_by_site": {s: int((g.date.diff().dt.days == 1).sum()) for s,g in test.groupby("site")},
                                         "bootstrap_unit": "joint calendar date blocks (28 days), preserving same-date shared NOAA proxy and all site rows"},
        "interpretation": ["预测误差改善是条件关联，不是传热机制证据。", "留站评估同时限制训练于2014-2019，测试于2020-2024；结果混合站点外推与时期外推。", "三站中11501000与11502500共享 OCHI 气温序列，误差天数不能作为独立气象样本。"],
    }
    (OUT / "recomputed_results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=lambda x: int(x) if isinstance(x, np.integer) else float(x) if isinstance(x, np.floating) else str(x)) + "\n")
    panel.to_csv(OUT / "recomputed_paired_panel.csv", index=False)
    rows=[]
    for target, models in point.items():
        for model, met in models.items():
            rows.append({"target":target,"model":model,**met})
    pd.DataFrame(rows).to_csv(OUT / "metrics_table.csv", index=False)
    print(json.dumps({"rows":len(panel),"metrics":point,"block_ci":block,"interaction":out["training_interaction_calendar_block_bootstrap"],"leave_site":leave_site},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
