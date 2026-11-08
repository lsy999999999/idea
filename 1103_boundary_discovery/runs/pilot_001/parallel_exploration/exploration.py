from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[3]
WS = ROOT / "runs/pilot_001/stages/r00_boundary/attempt-001/workspace"
DATA = WS / "data"
OUT = Path(__file__).resolve().parent
SITES = {
    "10396000": ("USR0000OPHI", "DONNER UND BLITZEN"),
    "11501000": ("USR0000OCHI", "SPRAGUE"),
    "11502500": ("USR0000OCHI", "WILLIAMSON BELOW SPRAGUE"),
}


def read_rdb(path: Path) -> pd.DataFrame:
    lines = [line for line in path.read_text(errors="replace").splitlines() if line and not line.startswith("#")]
    return pd.read_csv(io.StringIO("\n".join([lines[0], *lines[2:]])), sep="\t", dtype=str)


def read_ghcn(path: Path) -> pd.DataFrame:
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        if len(line) < 269:
            continue
        station, year, month, element = line[:11], int(line[11:15]), int(line[15:17]), line[17:21]
        if element not in {"TMAX", "TMIN"}:
            continue
        for day in range(1, 32):
            field = line[21 + (day - 1) * 8:29 + (day - 1) * 8]
            if len(field) < 8:
                continue
            value = int(field[:5])
            qflag = field[6]
            if value == -9999 or qflag.strip():
                continue
            try:
                date = pd.Timestamp(year=year, month=month, day=day)
            except ValueError:
                continue
            rows.append((station, date, element, value / 10.0))
    wide = pd.DataFrame(rows, columns=["air_station", "date", "element", "temp_c"])
    return wide.pivot_table(index=["air_station", "date"], columns="element", values="temp_c", aggfunc="first").reset_index()


def prepare_panel() -> pd.DataFrame:
    raw = read_rdb(DATA / "usgs_daily_values_2000_to_2026.rdb")
    # Columns are positional and consistent across the three site sections:
    # water max/code, min/code, mean/code, and discharge mean/code.
    colnames = ["agency", "site", "date", "water_max", "water_max_cd", "water_min", "water_min_cd", "water_mean", "water_mean_cd", "flow", "flow_cd"]
    raw = raw.iloc[:, :len(colnames)]
    raw.columns = colnames
    raw = raw[raw.site.isin(SITES)].copy()
    raw["date"] = pd.to_datetime(raw.date, errors="coerce")
    for c in ["water_max", "water_min", "water_mean", "flow"]:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    air_parts = []
    for site, (air_station, _) in SITES.items():
        air = read_ghcn(DATA / f"ghcn_{air_station}.dly")
        air = air[air.air_station.eq(air_station)].copy()
        air["air_mean"] = (air.TMAX + air.TMIN) / 2
        air["air_range"] = air.TMAX - air.TMIN
        air["site"] = site
        air_parts.append(air[["site", "date", "air_mean", "air_range"]])
    air = pd.concat(air_parts, ignore_index=True)
    panel = raw.merge(air, on=["site", "date"], how="inner")
    panel = panel[(panel.date.dt.year >= 2014) & (panel.date.dt.year <= 2024)].copy()
    panel["site_name"] = panel.site.map({s: v[1] for s, v in SITES.items()})
    panel["year"] = panel.date.dt.year
    panel["month"] = panel.date.dt.month.astype(str)
    panel["water_range"] = panel.water_max - panel.water_min
    panel["log_flow"] = np.log10(panel.flow.clip(lower=0) + 0.1)
    # Primary sample: approved values; estimated flow flagged A:e is retained, provisional is not.
    good = (
        panel.water_max_cd.fillna("").str.startswith("A")
        & panel.water_min_cd.fillna("").str.startswith("A")
        & panel.water_mean_cd.fillna("").str.startswith("A")
        & panel.flow_cd.fillna("").str.startswith("A")
    )
    return panel[good & panel[["water_max", "water_min", "water_mean", "flow", "air_mean", "air_range"]].notna().all(axis=1)].copy()


def make_model(categorical: list[str], numeric: list[str]):
    prep = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), numeric),
    ])
    return make_pipeline(prep, LinearRegression())


def metrics(y_true, y_pred) -> dict:
    return {
        "n": int(len(y_true)),
        "mae_c": float(mean_absolute_error(y_true, y_pred)),
        "rmse_c": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "r2": float(r2_score(y_true, y_pred)),
    }


def evaluate_time_holdout(df: pd.DataFrame, target: str, feature_sets: dict[str, list[str]]) -> dict:
    train = df[df.year.between(2014, 2019)].copy()
    test = df[df.year.between(2020, 2024)].copy()
    results = {}
    for name, features in feature_sets.items():
        model = make_model(["site", "month"], features)
        model.fit(train[["site", "month", *features]], train[target])
        pred = model.predict(test[["site", "month", *features]])
        results[name] = metrics(test[target], pred)
    return {"train_years": [2014, 2019], "test_years": [2020, 2024], "models": results}


def evaluate_site_holdout(df: pd.DataFrame, target: str, features: list[str]) -> dict:
    output = {}
    for site in SITES:
        train = df[(df.site != site) & df.year.between(2014, 2019)].copy()
        test = df[(df.site == site) & df.year.between(2020, 2024)].copy()
        # Deliberately omit station identity: this is a test of transfer without a site intercept.
        model = make_model(["month"], features)
        model.fit(train[["month", *features]], train[target])
        pred = model.predict(test[["month", *features]])
        output[site] = {"held_site": SITES[site][1], **metrics(test[target], pred)}
    return output


def evaluate_within_site_time_holdout(df: pd.DataFrame, target: str, features: list[str]) -> dict:
    output = {}
    for site in SITES:
        train = df[(df.site == site) & df.year.between(2014, 2019)].copy()
        test = df[(df.site == site) & df.year.between(2020, 2024)].copy()
        results = {}
        for name, cols in features.items():
            model = make_model(["month"], cols)
            model.fit(train[["month", *cols]], train[target])
            pred = model.predict(test[["month", *cols]])
            results[name] = metrics(test[target], pred)
        output[site] = {"site": SITES[site][1], "models": results}
    return output


def training_coefficients(df: pd.DataFrame, target: str) -> dict:
    train = df[df.year.between(2014, 2019)].copy()
    site_d = pd.get_dummies(train.site, prefix="site", drop_first=True, dtype=float)
    month_d = pd.get_dummies(train.month, prefix="month", drop_first=True, dtype=float)
    base = pd.concat([pd.Series(1.0, index=train.index, name="intercept"), site_d, month_d,
                      train[["air_mean", "log_flow", "air_range", "air_range_x_low_flow"]]], axis=1)
    x = base.to_numpy(float)
    y = train[target].to_numpy(float)
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    fitted = dict(zip(base.columns, coef))
    return {
        "fit_period": [2014, 2019],
        "target": target,
        "partial_slope_air_range_c_per_c": float(fitted["air_range"]),
        "additional_air_range_slope_at_low_flow_c_per_c": float(fitted["air_range_x_low_flow"]),
        "air_range_slope_at_low_flow_c_per_c": float(fitted["air_range"] + fitted["air_range_x_low_flow"]),
        "controls": ["site indicators", "month indicators", "air mean", "log10(discharge + 0.1)"],
        "n": int(len(train)),
    }


def export_time_holdout_predictions(df: pd.DataFrame) -> None:
    rows = []
    specs = {
        "water_mean": [
            ("base", ["air_mean", "log_flow"]),
            ("air_range", ["air_mean", "log_flow", "air_range"]),
            ("air_range_lowflow", ["air_mean", "log_flow", "air_range", "air_range_x_low_flow"]),
        ],
        "water_range": [
            ("base", ["air_mean", "log_flow"]),
            ("air_range", ["air_mean", "log_flow", "air_range"]),
            ("air_range_lowflow", ["air_mean", "log_flow", "air_range", "air_range_x_low_flow"]),
        ],
        "water_max": [
            ("base", ["air_mean", "log_flow"]),
            ("air_range", ["air_mean", "log_flow", "air_range"]),
            ("air_range_lowflow", ["air_mean", "log_flow", "air_range", "air_range_x_low_flow"]),
        ],
        "water_min": [
            ("base", ["air_mean", "log_flow"]),
            ("air_range", ["air_mean", "log_flow", "air_range"]),
            ("air_range_lowflow", ["air_mean", "log_flow", "air_range", "air_range_x_low_flow"]),
        ],
    }
    train = df[df.year.between(2014, 2019)].copy()
    test = df[df.year.between(2020, 2024)].copy()
    for target, models in specs.items():
        block = test[["date", "site", "year", target]].rename(columns={target: "observed"}).copy()
        for name, features in models:
            model = make_model(["site", "month"], features)
            model.fit(train[["site", "month", *features]], train[target])
            block[f"pred_{name}"] = model.predict(test[["site", "month", *features]])
        block["target"] = target
        rows.append(block)
    pd.concat(rows, ignore_index=True).to_csv(OUT / "heldout_predictions.csv", index=False)


def main():
    panel = prepare_panel()
    if panel.empty:
        raise RuntimeError("No paired approved observations after parsing.")
    panel["low_flow"] = 0
    cutoffs = {}
    for site, group in panel[panel.year.between(2014, 2019)].groupby("site"):
        cutoff = float(group.log_flow.quantile(0.25))
        cutoffs[site] = cutoff
        panel.loc[panel.site.eq(site), "low_flow"] = (panel.loc[panel.site.eq(site), "log_flow"] <= cutoff).astype(int)
    panel["air_range_x_low_flow"] = panel.air_range * panel.low_flow
    export_time_holdout_predictions(panel)

    mean_models = {
        "season_site_airmean_flow": ["air_mean", "log_flow"],
        "plus_air_diurnal_range": ["air_mean", "log_flow", "air_range"],
        "plus_range_x_low_flow": ["air_mean", "log_flow", "air_range", "air_range_x_low_flow"],
    }
    range_models = {
        "season_site_airmean_flow": ["air_mean", "log_flow"],
        "plus_air_diurnal_range": ["air_mean", "log_flow", "air_range"],
        "plus_range_x_low_flow": ["air_mean", "log_flow", "air_range", "air_range_x_low_flow"],
    }
    report = {
        "question": "Does atmospheric diurnal range predict stream daily temperature range beyond air mean, discharge, season, and site, and is this association stronger in low-flow conditions?",
        "data": {
            "period": [2014, 2024],
            "sites": {s: {"air_station": v[0], "description": v[1]} for s, v in SITES.items()},
            "approved_and_complete_rows": int(len(panel)),
            "rows_by_site_year": {f"{s}_{int(y)}": int(n) for (s, y), n in panel.groupby(["site", "year"]).size().items()},
            "primary_quality_rule": "Require water max/min/mean and flow flags beginning with A; retain A:e estimates, reject provisional; NOAA daily TMAX/TMIN require nonmissing values and blank qflag.",
            "low_flow_cutoffs_log10_cfs": cutoffs,
            "flow_flags": {str(k): int(v) for k, v in panel.flow_cd.value_counts().items()},
        },
        "temporal_holdout": {
            "water_mean": evaluate_time_holdout(panel, "water_mean", mean_models),
            "water_daily_range": evaluate_time_holdout(panel, "water_range", range_models),
            "water_daily_max": evaluate_time_holdout(panel, "water_max", range_models),
            "water_daily_min": evaluate_time_holdout(panel, "water_min", range_models),
        },
        "within_site_temporal_holdout": {
            "water_daily_range": evaluate_within_site_time_holdout(panel, "water_range", {
                "base": ["air_mean", "log_flow"],
                "plus_air_range": ["air_mean", "log_flow", "air_range"],
            }),
            "water_daily_max": evaluate_within_site_time_holdout(panel, "water_max", {
                "base": ["air_mean", "log_flow"],
                "plus_air_range": ["air_mean", "log_flow", "air_range"],
            }),
            "water_daily_min": evaluate_within_site_time_holdout(panel, "water_min", {
                "base": ["air_mean", "log_flow"],
                "plus_air_range": ["air_mean", "log_flow", "air_range"],
            }),
        },
        "training_partial_coefficients": {
            target: training_coefficients(panel, target)
            for target in ["water_range", "water_max", "water_min"]
        },
        "warm_season_sensitivity_may_sep": {
            "water_daily_range": evaluate_time_holdout(panel[panel.date.dt.month.between(5, 9)], "water_range", range_models),
            "water_daily_max": evaluate_time_holdout(panel[panel.date.dt.month.between(5, 9)], "water_max", range_models),
            "water_daily_min": evaluate_time_holdout(panel[panel.date.dt.month.between(5, 9)], "water_min", range_models),
        },
        "site_holdout": {
            "water_daily_range_base": evaluate_site_holdout(panel, "water_range", ["air_mean", "log_flow"]),
            "water_daily_range_plus_air_range": evaluate_site_holdout(panel, "water_range", ["air_mean", "log_flow", "air_range"]),
            "water_daily_max_base": evaluate_site_holdout(panel, "water_max", ["air_mean", "log_flow"]),
            "water_daily_max_plus_air_range": evaluate_site_holdout(panel, "water_max", ["air_mean", "log_flow", "air_range"]),
        },
        "sensitivity_strict_approved_only": {},
        "interpretation_guardrail": "All statistics are exploratory: coverage audit already examined these source files and only three selected sites are analyzed. Association/prediction does not identify heat transfer mechanism.",
    }

    # Sensitivity removes estimated flows and any non-exact approval code.
    strict = panel[
        panel.water_max_cd.eq("A") & panel.water_min_cd.eq("A") & panel.water_mean_cd.eq("A") & panel.flow_cd.eq("A")
    ].copy()
    strict["low_flow"] = 0
    strict_cutoffs = {}
    for site, group in strict[strict.year.between(2014, 2019)].groupby("site"):
        cutoff = float(group.log_flow.quantile(0.25))
        strict_cutoffs[site] = cutoff
        strict.loc[strict.site.eq(site), "low_flow"] = (strict.loc[strict.site.eq(site), "log_flow"] <= cutoff).astype(int)
    strict["air_range_x_low_flow"] = strict.air_range * strict.low_flow
    report["sensitivity_strict_approved_only"] = {
        "n_rows": int(len(strict)),
        "low_flow_cutoffs_log10_cfs": strict_cutoffs,
        "water_daily_range": evaluate_time_holdout(strict, "water_range", range_models),
        "water_daily_max": evaluate_time_holdout(strict, "water_max", range_models),
    }

    panel_path = OUT / "paired_daily_panel.csv"
    panel.to_csv(panel_path, index=False)
    (OUT / "numeric_results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"rows": len(panel), "time_range_test": report["temporal_holdout"]["water_daily_range"], "site_range_base": report["site_holdout"]["water_daily_range_base"], "site_range_plus_air_range": report["site_holdout"]["water_daily_range_plus_air_range"], "strict": report["sensitivity_strict_approved_only"]["water_daily_range"]}, indent=2))


if __name__ == "__main__":
    main()
