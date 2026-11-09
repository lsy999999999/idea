import os

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["NUMEXPR_NUM_THREADS"] = "4"

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import KFold

PATH = "measurements.csv"
if not os.path.exists(PATH):
    raise FileNotFoundError(f"Expected {PATH} in the current working directory.")

df = pd.read_csv(PATH)
print("Columns:", list(df.columns))


def find_col(candidates):
    lower = {str(c).strip().lower(): c for c in df.columns}
    for name in candidates:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


phase_col = find_col(["mean_phase", "mean phase", "phase"])
scan_col = find_col(["scan"])
stokes = [find_col([name]) for name in ("S1", "S2", "S3")]
dop_col = find_col(["DOP"])

if phase_col is None or scan_col is None:
    raise ValueError("Could not identify mean-phase and scan columns.")
if any(col is None for col in stokes):
    raise ValueError("Required Stokes columns S1, S2, S3 were not found.")

scan_labels = df[scan_col].astype(str).str.strip().str.lower()
is_mean_scan = scan_labels.str.contains("mean_phase|mean phase", regex=True, na=False)
scan = df.loc[is_mean_scan].copy()
scan["_source_row"] = np.flatnonzero(is_mean_scan.to_numpy())

numeric_cols = [phase_col] + stokes + ([dop_col] if dop_col is not None else [])
for col in numeric_cols:
    scan[col] = pd.to_numeric(scan[col], errors="coerce")

scan = scan.dropna(subset=[phase_col] + stokes).copy()
if len(scan) < 12:
    raise ValueError(f"Too few valid mean-phase rows ({len(scan)}).")

# Keep original source row order for the order-proxy model; sort only for phase plots/CV.
scan = scan.sort_values(phase_col, kind="mergesort").reset_index(drop=True)
phi = scan[phase_col].to_numpy(dtype=float)
y_all = scan[stokes].to_numpy(dtype=float)
source_order = scan["_source_row"].to_numpy(dtype=float)
norm2 = np.sum(y_all**2, axis=1)

print(f"\nMean-phase scan rows: {len(scan)} (separate scan; descriptive, no repeats)")
print(f"Mean-phase range: {phi.min():.6f} to {phi.max():.6f} rad")
print(
    "Note: source row order is only an acquisition-order proxy; its meaning "
    "is not established by the supplied file."
)
for j, name in enumerate(stokes):
    print(
        f"{name}: mean={y_all[:, j].mean():.6f}, sd={y_all[:, j].std(ddof=1):.6f}, "
        f"min={y_all[:, j].min():.6f}, max={y_all[:, j].max():.6f}"
    )
print(
    f"Stokes squared norm: mean={norm2.mean():.6f}, sd={norm2.std(ddof=1):.6f}, "
    f"min={norm2.min():.6f}, max={norm2.max():.6f}"
)

dop = None
if dop_col is not None:
    dop = scan[dop_col].to_numpy(dtype=float)
    valid_dop = np.isfinite(dop)
    print(
        f"DOP (native mean-phase scale): n={valid_dop.sum()}, "
        f"mean={np.nanmean(dop):.6f}, sd={np.nanstd(dop, ddof=1):.6f}, "
        f"min={np.nanmin(dop):.6f}, max={np.nanmax(dop):.6f}"
    )
    paired = valid_dop & np.isfinite(norm2)
    if paired.sum() > 2 and np.std(dop[paired]) > 0 and np.std(norm2[paired]) > 0:
        corr = np.corrcoef(dop[paired], norm2[paired])[0, 1]
        print(
            "Descriptive Pearson(DOP, Stokes squared norm): "
            f"{corr:.6f} (association only; quantities are not assumed equivalent)"
        )
    else:
        print("Descriptive Pearson(DOP, Stokes squared norm): undefined")


def fourier_features(x, harmonics=3):
    return np.column_stack(
        [fn(k * x) for k in range(1, harmonics + 1) for fn in (np.sin, np.cos)]
    )


def contiguous_phase_folds(x, n_splits):
    """Return phase-ordered contiguous holdout blocks and their complementary training rows."""
    order = np.argsort(x, kind="mergesort")
    blocks = np.array_split(order, n_splits)
    return [(np.setdiff1d(order, test, assume_unique=True), test) for test in blocks]


# Contiguous phase blocks test interpolation across omitted phase regions, not random-row fit.
# This is descriptive predictive validation on one scan, not repeat-based inference.
n_splits = min(5, len(scan) // 3)
if n_splits < 2:
    raise ValueError("Insufficient rows for contiguous phase-block validation.")
folds = contiguous_phase_folds(phi, n_splits)

phase_scale = max(np.ptp(phi), 1.0)
phase_scaled = (phi - phi.mean()) / phase_scale
order_scale = max(np.ptp(source_order), 1.0)
order_scaled = (source_order - source_order.mean()) / order_scale


def constant_features(idx):
    return np.ones((len(idx), 1))


def phase_linear_features(idx):
    return phase_scaled[idx, None]


def fourier3_features(idx):
    return fourier_features(phi[idx], harmonics=3)


def order_features(idx):
    return order_scaled[idx, None]


models = {
    "constant": constant_features,
    "phase-linear": phase_linear_features,
    "Fourier k=1..3": fourier3_features,
    "source-row-order linear (proxy)": order_features,
}

print("\nContiguous phase-block CV (exploratory; not independent-repeat evidence):")
for j, name in enumerate(stokes):
    y = y_all[:, j]
    for model_name, feature_fn in models.items():
        pred = np.full(len(scan), np.nan)
        for train, test in folds:
            model = LinearRegression().fit(feature_fn(train), y[train])
            pred[test] = model.predict(feature_fn(test))
        valid = np.isfinite(pred)
        rmse = mean_squared_error(y[valid], pred[valid]) ** 0.5
        score = r2_score(y[valid], pred[valid])
        print(f"{name:>2} | {model_name:<32} RMSE={rmse:.6f} R2={score:.6f}")

fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
grid = np.linspace(phi.min(), phi.max(), 500)

for j, name in enumerate(stokes):
    ax = axes.flat[j]
    ax.plot(phi, y_all[:, j], "o", ms=3, label="observed")
    fit = LinearRegression().fit(fourier3_features(np.arange(len(scan))), y_all[:, j])
    grid_features = fourier_features(grid, harmonics=3)
    ax.plot(grid, fit.predict(grid_features), lw=1.5, label="Fourier k=1..3")
    ax.set(xlabel="Mean phase (rad)", ylabel=name)
    ax.legend(frameon=False)

ax = axes.flat[3]
ax.plot(phi, norm2, "o-", ms=3, label="S1^2 + S2^2 + S3^2")
ax.set(xlabel="Mean phase (rad)", ylabel="Stokes squared norm")
if dop is not None:
    ax2 = ax.twinx()
    ax2.plot(phi, dop, color="tab:red", alpha=0.7, label="exported DOP")
    ax2.set_ylabel("Exported DOP (native scale)")
fig.suptitle("Supplied mean-phase scan: descriptive evidence, not independent repeats")
fig.savefig("mean_phase_analysis.png", dpi=160)
plt.close(fig)
print("\nSaved visualization: mean_phase_analysis.png")
