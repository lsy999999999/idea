"""Quick 2024 warm-season harmonic summaries from the pilot's raw IV files."""
from __future__ import annotations

import io
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
RUN = HERE.parent
IV_ROOT = RUN / "stages/r01_boundary/attempt-001/workspace/data"
PANEL = RUN / "parallel_exploration/paired_daily_panel.csv"
FILES = {
    "10396000": "iv_10396000_2024_may_sep.rdb",
    "11501000": "iv_11501000_2024_may_sep.rdb",
    "11502500": "iv_11502500_2024_may_sep.rdb",
}


def read_rdb(path: Path) -> pd.DataFrame:
    lines = [line for line in path.read_text(errors="replace").splitlines()
             if line and not line.startswith("#")]
    return pd.read_csv(io.StringIO("\n".join([lines[0], *lines[2:]])), sep="\t", dtype=str)


def daily_harmonics(site: str, filename: str) -> pd.DataFrame:
    frame = read_rdb(IV_ROOT / filename)
    value = next(column for column in frame.columns if column.endswith("_00010"))
    frame = frame[frame[f"{value}_cd"].fillna("").eq("A")].copy()
    frame["temperature"] = pd.to_numeric(frame[value], errors="coerce")
    frame["datetime"] = pd.to_datetime(frame["datetime"], format="%Y-%m-%d %H:%M", errors="coerce")
    frame = frame.dropna(subset=["temperature", "datetime"])
    frame["date"] = frame["datetime"].dt.strftime("%Y-%m-%d")
    frame["hour"] = frame["datetime"].dt.hour + frame["datetime"].dt.minute / 60
    rows = []
    for date, day in frame.groupby("date"):
        if len(day) < 87:
            continue
        hour = day["hour"].to_numpy()
        temp = day["temperature"].to_numpy()
        design = np.column_stack([
            np.ones(len(day)),
            np.sin(2 * np.pi * hour / 24),
            np.cos(2 * np.pi * hour / 24),
        ])
        beta = np.linalg.lstsq(design, temp, rcond=None)[0]
        peak_hour = (math.atan2(beta[1], beta[2]) * 24 / (2 * math.pi)) % 24
        rows.append({
            "date": date,
            "site": site,
            "harmonic_amplitude_c": float(np.hypot(beta[1], beta[2])),
            "harmonic_peak_hour_local": peak_hour,
            "observed_range_c": float(temp.max() - temp.min()),
            "observed_max_hour_local": float(hour[temp.argmax()]),
            "observed_min_hour_local": float(hour[temp.argmin()]),
            "n_15min_values": int(len(day)),
        })
    return pd.DataFrame(rows)


def partial_corr(x: pd.Series, y: pd.Series, controls: pd.DataFrame) -> float:
    categorical = pd.get_dummies(controls["month"].astype(str), dtype=float)
    design = np.column_stack([
        np.ones(len(controls)), categorical.to_numpy(),
        controls[["air_mean", "air_range"]].to_numpy(),
    ])
    xr = x.to_numpy() - design @ np.linalg.lstsq(design, x.to_numpy(), rcond=None)[0]
    yr = y.to_numpy() - design @ np.linalg.lstsq(design, y.to_numpy(), rcond=None)[0]
    return float(np.corrcoef(xr, yr)[0, 1])


def main() -> None:
    site_days = pd.concat([daily_harmonics(site, file) for site, file in FILES.items()], ignore_index=True)
    summary = {}
    for site, group in site_days.groupby("site"):
        summary[site] = {
            "days_with_at_least_87_of_96_values": int(len(group)),
            "median_harmonic_amplitude_c": float(group["harmonic_amplitude_c"].median()),
            "median_observed_range_c": float(group["observed_range_c"].median()),
            "median_harmonic_peak_hour_local": float(group["harmonic_peak_hour_local"].median()),
            "median_observed_max_hour_local": float(group["observed_max_hour_local"].median()),
            "median_observed_min_hour_local": float(group["observed_min_hour_local"].median()),
        }

    sprague = site_days[site_days.site.eq("11501000")].set_index("date")
    williamson = site_days[site_days.site.eq("11502500")].set_index("date")
    pair = sprague.join(williamson, lsuffix="_sprague", rsuffix="_williamson", how="inner")
    phase_shift = ((pair.harmonic_peak_hour_local_williamson
                    - pair.harmonic_peak_hour_local_sprague + 12) % 24) - 12
    amp_ratio = pair.harmonic_amplitude_c_williamson / pair.harmonic_amplitude_c_sprague

    panel = pd.read_csv(PANEL)
    panel["site"] = panel["site"].astype(str)
    panel["date"] = pd.to_datetime(panel["date"]).dt.strftime("%Y-%m-%d")
    warm = panel[panel["date"].str.startswith("2024-") & panel["site"].isin(["11501000", "11502500"])]
    flow = warm.pivot(index="date", columns="site", values="flow")
    share = flow["11501000"] / flow["11502500"]
    weather = warm.drop_duplicates("date").set_index("date")[["month", "air_mean", "air_range"]]
    joined = pair.join(share.rename("sprague_to_williamson_flow_ratio")).join(weather).dropna()
    ratio = (joined.harmonic_amplitude_c_williamson
             / joined.harmonic_amplitude_c_sprague)
    lag = ((joined.harmonic_peak_hour_local_williamson
            - joined.harmonic_peak_hour_local_sprague + 12) % 24) - 12
    output = {
        "scope": "One exploratory warm season (2024), 15-minute approved USGS water-temperature values only; not an inferential test.",
        "input_files": [str(IV_ROOT / file) for file in FILES.values()] + [str(PANEL)],
        "harmonic_method": "Per local date fit c + a*sin(2*pi*hour/24) + b*cos(2*pi*hour/24); amplitude=sqrt(a^2+b^2); peak phase from atan2(a,b). Retain days with >=87 of 96 observations and A qualifier.",
        "site_summaries": summary,
        "sprague_williamson_pair": {
            "description": "11501000 Sprague River near Chiloquin versus 11502500 Williamson River below Sprague River near Chiloquin; both paired to NOAA GHCN OCHI.",
            "paired_days_without_flow": int(len(pair)),
            "paired_days_with_flow_ratio": int(len(joined)),
            "median_williamson_to_sprague_harmonic_amplitude_ratio": float(amp_ratio.median()),
            "median_williamson_peak_shift_hours": float(phase_shift.median()),
            "median_q_sprague_over_q_williamson": float(joined.sprague_to_williamson_flow_ratio.median()),
            "raw_spearman_flow_ratio_vs_amplitude_ratio": float(joined.sprague_to_williamson_flow_ratio.corr(ratio, method="spearman")),
            "raw_spearman_flow_ratio_vs_phase_shift": float(joined.sprague_to_williamson_flow_ratio.corr(lag, method="spearman")),
            "partial_corr_flow_ratio_vs_amplitude_ratio_controlling_month_air_mean_air_range": partial_corr(joined.sprague_to_williamson_flow_ratio, ratio, joined),
            "partial_corr_flow_ratio_vs_phase_shift_controlling_month_air_mean_air_range": partial_corr(joined.sprague_to_williamson_flow_ratio, lag, joined),
        },
        "interpretation": "Raw flow-ratio associations are confounded by month and shared daily air summaries in this one-year check; partial correlations are descriptive and do not establish or exclude mixing.",
    }
    (HERE / "quick_check.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
