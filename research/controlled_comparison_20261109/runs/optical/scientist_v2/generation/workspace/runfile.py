import os
working_dir='/home/lsy/ideas_controlled_20261109/runs/optical/scientist_v2/generation/workspace'
os.chdir(working_dir)
import os

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["NUMEXPR_NUM_THREADS"] = "4"

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

PATH = "measurements.csv"
df = pd.read_csv(PATH)


def find_col(names):
    cols = {str(c).strip().lower(): c for c in df.columns}
    return next((cols[n.lower()] for n in names if n.lower() in cols), None)


phase_col = find_col(["mean_phase", "mean phase", "phase"])
scan_col = find_col(["scan"])
stokes_cols = [find_col([s]) for s in ("S1", "S2", "S3")]
dop_col = find_col(["DOP"])
if phase_col is None or scan_col is None or any(c is None for c in stokes_cols):
    raise ValueError("Required scan, mean-phase, and Stokes columns were not found.")

labels = df[scan_col].astype(str).str.strip().str.lower()
mask = labels.str.contains("mean_phase|mean phase", regex=True, na=False)
scan = df.loc[mask].copy()
for c in [phase_col, *stokes_cols] + ([dop_col] if dop_col else []):
    scan[c] = pd.to_numeric(scan[c], errors="coerce")
scan = (
    scan.dropna(subset=[phase_col, *stokes_cols])
    .sort_values(phase_col, kind="mergesort")
    .reset_index(drop=True)
)

phi = scan[phase_col].to_numpy(float)
Y = scan[stokes_cols].to_numpy(float)
norm2 = np.sum(Y**2, axis=1)
print(
    f"Mean-phase scan: n={len(scan)}, phase range=[{phi.min():.6f}, {phi.max():.6f}] rad"
)
for j, name in enumerate(("S1", "S2", "S3")):
    print(
        f"{name}: mean={Y[:, j].mean():.6f}, sd={Y[:, j].std(ddof=1):.6f}, "
        f"min={Y[:, j].min():.6f}, max={Y[:, j].max():.6f}"
    )
print(
    f"Stokes squared norm: mean={norm2.mean():.6f}, sd={norm2.std(ddof=1):.6f}, "
    f"min={norm2.min():.6f}, max={norm2.max():.6f}"
)

if dop_col:
    dop = scan[dop_col].to_numpy(float)
    valid = np.isfinite(dop)
    print(
        f"DOP (native scan scale): n={valid.sum()}, mean={np.nanmean(dop):.6f}, "
        f"sd={np.nanstd(dop, ddof=1):.6f}, min={np.nanmin(dop):.6f}, "
        f"max={np.nanmax(dop):.6f}"
    )
    paired = valid & np.isfinite(norm2)
    if paired.sum() > 2 and np.std(dop[paired]) > 0 and np.std(norm2[paired]) > 0:
        print(
            f"Descriptive Pearson correlation(DOP, squared norm)="
            f"{np.corrcoef(dop[paired], norm2[paired])[0, 1]:.6f}"
        )

# Endpoint directions are compared directly; the endpoints are not treated as repeats.
endpoint_indices = [np.flatnonzero(phi == p)[0] for p in (phi.min(), phi.max())]
endpoint_dirs = []
for i in endpoint_indices:
    length = np.linalg.norm(Y[i])
    endpoint_dirs.append(Y[i] / length if length > 0 else np.full(3, np.nan))
direction_gap = np.linalg.norm(endpoint_dirs[0] - endpoint_dirs[1])
print(
    f"Endpoint direction Euclidean gap (0 vs sampled maximum phase): {direction_gap:.6f}"
)


def features(x, kind):
    if kind == "constant":
        return np.ones((len(x), 1))
    if kind == "linear phase":
        return ((x - phi.mean()) / max(np.ptp(phi), 1e-12))[:, None]
    if kind == "Fourier k=1..3":
        return np.column_stack(
            [f(k * x) for k in range(1, 4) for f in (np.sin, np.cos)]
        )
    raise ValueError(kind)


# Each test fold is a contiguous interval in sorted phase; metrics are descriptive.
folds = np.array_split(np.arange(len(scan)), min(5, max(2, len(scan) // 3)))
print("Contiguous phase-block CV (exploratory; no replicate-based inference):")
for j, name in enumerate(("S1", "S2", "S3")):
    y = Y[:, j]
    for kind in ("constant", "linear phase", "Fourier k=1..3"):
        pred = np.full(len(y), np.nan)
        for test in folds:
            train = np.setdiff1d(np.arange(len(y)), test, assume_unique=True)
            model = LinearRegression().fit(features(phi[train], kind), y[train])
            pred[test] = model.predict(features(phi[test], kind))
        print(
            f"{name} | {kind}: RMSE={mean_squared_error(y, pred)**0.5:.6f}, "
            f"R2={r2_score(y, pred):.6f}"
        )
print("Interpretation: one scan is descriptive; phase locking, drift, and hysteresis")
print(
    "require repeated randomized and ascending/descending sweeps with acquisition order recorded."
)
