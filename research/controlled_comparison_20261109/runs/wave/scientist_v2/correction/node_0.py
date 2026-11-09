import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import linregress

path = Path("measurements.csv")
df = pd.read_csv(path)


def column(*names):
    for name in names:
        if name in df.columns:
            return name
    raise KeyError(f"Missing expected column; tried {names}. Found: {list(df.columns)}")


tcol = column("time_s", "time")
wcol = column("correlation_width", "width", "fwhm")
time = pd.to_numeric(df[tcol], errors="coerce").to_numpy()
width = pd.to_numeric(df[wcol], errors="coerce").to_numpy()
valid = np.isfinite(time) & np.isfinite(width)
time, width = time[valid], width[valid]
order = np.argsort(time)
time, width = time[order], width[order]

dtime = np.diff(time)
dtime = dtime[np.isfinite(dtime) & (dtime > 0)]
dt = float(np.median(dtime)) if len(dtime) else None
frequency = 1.0 / dt if dt else None

# The source normalization is width[1] / width; the constant numerator
# does not alter the reciprocal dependence on width.
positive = width > 0
wref = float(width[1]) if len(width) > 1 else None
inv = wref / width[positive] if wref is not None else np.array([])
doubling_ratio = 0.5  # inv(2*w) / inv(w), directly from the stated formula.

# Sensitivity of descriptive log-log slopes to the chosen interval.
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
    "data_file": str(path),
    "items": [
        {
            "id": "W1",
            "judgment": "Incorrect",
            "corrected_values": {
                "time_unit": "seconds, per supplied data dictionary",
                "sample_count": int(len(time)),
                "median_sample_interval_s": dt,
                "estimated_sampling_frequency_hz": frequency,
                "first_to_last_elapsed_s": (
                    float(time[-1] - time[0]) if len(time) else None
                ),
            },
            "implication": "Do not interpret the time axis as milliseconds or report 300000 Hz; unit scaling changes all temporal interpretations.",
        },
        {
            "id": "W2",
            "judgment": "Incorrect",
            "corrected_values": {
                "source_definition": "width[1] / width",
                "inverse_ratio_after_width_doubles": doubling_ratio,
                "effect": "doubling width halves the normalized inverse correlation length",
            },
            "implication": "This normalization is reciprocal in width; it is not a fitted exponent or an independently estimated length.",
        },
        {
            "id": "W3",
            "judgment": "Correct",
            "corrected_values": {
                "temporal_samples_in_csv": int(len(time)),
                "independent_physical_realizations_established": False,
            },
            "implication": "Treat this export as a time series; unavailable run identifiers and aggregation details prevent an independence claim.",
        },
        {
            "id": "W4",
            "judgment": "Unsupported / not identifiable from this record",
            "corrected_values": {
                "finite_record_log_log_slope_sensitivity": fit_results,
                "universal_asymptotic_exponent_established": False,
            },
            "implication": "Window-dependent fits can motivate follow-up tests, but this single finite record cannot establish universality across size or preparation.",
        },
    ],
}

Path("audit.json").write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")

fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].plot(time, width, lw=1)
ax[0].set(xlabel="Time (s)", ylabel="Correlation width", title="Observed width")
ax[1].scatter(width[positive], inv, s=8, alpha=0.5)
ax[1].set(
    xlabel="Correlation width",
    ylabel="width[1] / width",
    title="Source inverse-width normalization",
)
fig.tight_layout()
fig.savefig("audit_diagnostics.png", dpi=160)
plt.close(fig)

print(
    json.dumps(
        {
            "sample_count": int(len(time)),
            "median_interval_s": dt,
            "estimated_frequency_hz": frequency,
            "width_doubling_inverse_ratio": doubling_ratio,
            "descriptive_fit_sensitivity": fit_results,
            "audit_file": "audit.json",
            "plot_file": "audit_diagnostics.png",
        },
        indent=2,
        allow_nan=False,
    )
)
