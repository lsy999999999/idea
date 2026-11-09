import os
working_dir='/home/lsy/ideas_controlled_20261109/runs/wave/scientist_v2/correction/workspace'
os.chdir(working_dir)
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import linregress

df = pd.read_csv("measurements.csv")


def find_column(*names):
    for name in names:
        if name in df.columns:
            return name
    raise KeyError(f"Expected one of {names}; found {list(df.columns)}")


time_col = find_column("time_s", "time")
width_col = find_column("correlation_width", "width", "fwhm")

time = pd.to_numeric(df[time_col], errors="coerce").to_numpy()
width = pd.to_numeric(df[width_col], errors="coerce").to_numpy()
valid = np.isfinite(time) & np.isfinite(width)
time, width = time[valid], width[valid]
order = np.argsort(time)
time, width = time[order], width[order]

gaps = np.diff(time)
gaps = gaps[np.isfinite(gaps) & (gaps > 0)]
dt = float(np.median(gaps)) if len(gaps) else None
frequency = 1.0 / dt if dt else None

fit_results = []
for lo, hi in [(0.1, 2.0), (0.5, 3.0), (1.0, 5.0), (2.0, 7.0)]:
    mask = (time >= lo) & (time <= hi) & (width > 0)
    if mask.sum() >= 3:
        fit = linregress(np.log(time[mask]), np.log(width[mask]))
        fit_results.append(
            {
                "time_window_s": [lo, hi],
                "n_samples": int(mask.sum()),
                "log_log_slope": float(fit.slope),
                "r_squared": float(fit.rvalue**2),
            }
        )

audit = {
    "data_file": "measurements.csv",
    "items": [
        {
            "id": "W1",
            "judgment": "Incorrect",
            "corrected_values": {
                "time_unit": "seconds, as specified by the supplied data dictionary",
                "sample_count": int(len(time)),
                "median_sample_interval_s": dt,
                "estimated_sampling_frequency_hz": frequency,
                "elapsed_span_s": float(time[-1] - time[0]) if len(time) else None,
            },
            "implication": "The measurements indicate approximately 300 samples/s, not 300000 Hz; the stated milliseconds unit is incorrect.",
        },
        {
            "id": "W2",
            "judgment": "Incorrect",
            "corrected_values": {
                "source_definition": "width[1] / width",
                "inverse_ratio_when_width_doubles": 0.5,
                "effect": "doubling width halves the normalized inverse correlation length",
            },
            "implication": "The normalization is reciprocal in width and is not a fitted scaling exponent.",
        },
        {
            "id": "W3",
            "judgment": "Correct",
            "corrected_values": {
                "temporal_samples": int(len(time)),
                "independent_physical_realizations_established": False,
            },
            "implication": "Treat these as temporally ordered measurements; the export does not establish independent runs or realizations.",
        },
        {
            "id": "W4",
            "judgment": "Unsupported / not identifiable from this record",
            "corrected_values": {
                "finite_record_log_log_fits": fit_results,
                "universal_asymptotic_exponent_established": False,
            },
            "implication": "Window-specific slopes may motivate tests, but universality requires evidence across system sizes and preparations, which this record does not provide.",
        },
    ],
}

Path("audit.json").write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")
print(
    json.dumps(
        {
            "sample_count": int(len(time)),
            "median_interval_s": dt,
            "estimated_frequency_hz": frequency,
            "inverse_normalization_ratio_after_width_doubles": 0.5,
            "finite_record_fit_sensitivity": fit_results,
            "audit_file": "audit.json",
        },
        indent=2,
        allow_nan=False,
    )
)
