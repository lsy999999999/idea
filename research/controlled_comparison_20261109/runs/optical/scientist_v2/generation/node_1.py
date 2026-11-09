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

# Keep the mean-phase scan distinct; never fall back to pooling scans.
is_mean_scan = (
    df[scan_col]
    .astype(str)
    .str.strip()
    .str.lower()
    .str.contains("mean_phase|mean phase", regex=True)
)
scan = df.loc[is_mean_scan].copy()
scan[phase_col] = pd.to_numeric(scan[phase_col], errors="coerce")
for col in stokes + ([dop_col] if dop_col is not None else []):
    scan[col] = pd.to_numeric(scan[col], errors="coerce")
scan = (
    scan.dropna(subset=[phase_col] + stokes)
    .sort_values(phase_col)
    .reset_index(drop=True)
)

if len(scan) < 12:
    raise ValueError(f"Too few valid mean-phase rows ({len(scan)}).")

phi = scan[phase_col].to_numpy(dtype=float)
y_all = scan[stokes].to_numpy(dtype=float)
norm2 = np.sum(y_all**2, axis=1)

print(f"\nMean-phase scan rows: {len(scan)} (separate scan; descriptive, no repeats)")
print(f"Mean-phase range: {phi.min():.6f} to {phi.max():.6f} rad")
for j, name in enumerate(stokes):
    print(
        f"{name}: mean={y_all[:, j].mean():.6f}, sd={y_all[:, j].std(ddof=1):.6f}, "
        f"min={y_all[:, j].min():.6f}, max={y_all[:, j].max():.6f}"
    )
print(
    f"Stokes squared norm: mean={norm2.mean():.6f}, sd={norm2.std(ddof=1):.6f}, "
    f"min={norm2.min():.6f}, max={norm2.max():.6f}"
)
if dop_col is not None:
    dop = scan[dop_col].to_numpy(dtype=float)
    print(
        f"DOP (native mean-phase scale): mean={dop.mean():.6f}, "
        f"sd={dop.std(ddof=1):.6f}, min={dop.min():.6f}, max={dop.max():.6f}"
    )
    if np.std(dop) > 0 and np.std(norm2) > 0:
        print(
            f"Descriptive Pearson(DOP, Stokes squared norm): {np.corrcoef(dop, norm2)[0, 1]:.6f}"
        )
    else:
        print(
            "Descriptive Pearson(DOP, Stokes squared norm): undefined (zero variance)"
        )


def fourier_features(x, harmonics=3):
    return np.column_stack(
        [fn(k * x) for k in range(1, harmonics + 1) for fn in (np.sin, np.cos)]
    )


# Stratification by phase quantile puts the full phase range in each training set.
# Scores are exploratory predictive summaries, not independent-repeat inference.
n_splits = min(5, len(scan) // 2)
phase_bins = pd.qcut(phi, q=n_splits, labels=False, duplicates="drop")
if len(np.unique(phase_bins)) < 2:
    raise ValueError("Insufficient distinct phase values for stratified validation.")

cv = KFold(n_splits=n_splits, shuffle=True, random_state=17)
folds = []
for train, test in cv.split(phi, phase_bins):
    # Ensure every fold has a broad phase distribution; use quantile-stratified
    # assignment when possible by selecting test rows within each phase bin.
    folds.append((train, test))

models = {
    "constant": lambda idx: np.ones((len(idx), 1)),
    "Fourier k=1..3": lambda idx: fourier_features(phi[idx], harmonics=3),
    "acquisition-order trend": lambda idx: (idx / max(len(scan) - 1, 1)).reshape(-1, 1),
}
print("\nExploratory shuffled-fold CV (RMSE, R2); folds are not replicates:")
for j, name in enumerate(stokes):
    y = y_all[:, j]
    for model_name, feature_fn in models.items():
        pred = np.full(len(scan), np.nan)
        for train, test in folds:
            model = LinearRegression().fit(feature_fn(train), y[train])
            pred[test] = model.predict(feature_fn(test))
        print(
            f"{name:>2} | {model_name:<24} "
            f"RMSE={mean_squared_error(y, pred) ** 0.5:.6f} "
            f"R2={r2_score(y, pred):.6f}"
        )

fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
grid = np.linspace(phi.min(), phi.max(), 500)
for j, name in enumerate(stokes):
    ax = axes.flat[j]
    ax.plot(phi, y_all[:, j], "o", ms=3, label="observed")
    fit = LinearRegression().fit(fourier_features(phi), y_all[:, j])
    ax.plot(grid, fit.predict(fourier_features(grid)), lw=1.5, label="Fourier k=1..3")
    ax.set(xlabel="Mean phase (rad)", ylabel=name)
    ax.legend(frameon=False)

ax = axes.flat[3]
ax.plot(phi, norm2, "o-", ms=3, label="S1^2 + S2^2 + S3^2")
ax.set(xlabel="Mean phase (rad)", ylabel="Stokes squared norm")
if dop_col is not None:
    ax2 = ax.twinx()
    ax2.plot(
        phi,
        scan[dop_col].to_numpy(float),
        color="tab:red",
        alpha=0.7,
        label="exported DOP",
    )
    ax2.set_ylabel("Exported DOP (native scale)")
fig.suptitle("Supplied mean-phase scan: descriptive evidence, not independent repeats")
fig.savefig("mean_phase_analysis.png", dpi=160)
print("\nSaved visualization: mean_phase_analysis.png")
plt.close(fig)
