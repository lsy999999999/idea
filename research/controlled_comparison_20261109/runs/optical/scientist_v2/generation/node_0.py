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
if phase_col is None:
    raise ValueError("Could not identify mean-phase column.")
if scan_col is None:
    raise ValueError("Could not identify scan column.")

scan = df[df[scan_col].astype(str).str.lower().str.contains("mean")].copy()
if scan.empty:
    scan = df[df[phase_col].notna()].copy()
scan[phase_col] = pd.to_numeric(scan[phase_col], errors="coerce")
scan = scan.dropna(subset=[phase_col]).sort_values(phase_col).reset_index(drop=True)

stokes = [find_col([x]) for x in ("S1", "S2", "S3")]
dop_col = find_col(["DOP"])
if any(c is None for c in stokes):
    raise ValueError("Required Stokes columns S1, S2, S3 were not found.")
for c in stokes + ([dop_col] if dop_col else []):
    scan[c] = pd.to_numeric(scan[c], errors="coerce")
scan = scan.dropna(subset=stokes).reset_index(drop=True)
if len(scan) < 12:
    raise ValueError(f"Too few valid mean-phase rows ({len(scan)}).")

phi = scan[phase_col].to_numpy(float)
y_all = scan[stokes].to_numpy(float)
norm2 = np.sum(y_all**2, axis=1)

print(f"\nMean-phase rows: {len(scan)}")
for j, name in enumerate(stokes):
    print(
        f"{name}: mean={np.mean(y_all[:, j]):.6f}, sd={np.std(y_all[:, j], ddof=1):.6f}, "
        f"min={np.min(y_all[:, j]):.6f}, max={np.max(y_all[:, j]):.6f}"
    )
print(
    f"Stokes squared norm: mean={norm2.mean():.6f}, sd={norm2.std(ddof=1):.6f}, "
    f"min={norm2.min():.6f}, max={norm2.max():.6f}"
)
if dop_col:
    dop = scan[dop_col].to_numpy(float)
    print(
        f"DOP (scan's exported scale): mean={dop.mean():.6f}, sd={dop.std(ddof=1):.6f}, "
        f"min={dop.min():.6f}, max={dop.max():.6f}"
    )
    print(
        f"Pearson correlation DOP vs Stokes squared norm: {np.corrcoef(dop, norm2)[0, 1]:.6f}"
    )


def fourier_features(x, harmonics=3):
    return np.column_stack(
        [f(k * x) for k in range(1, harmonics + 1) for f in (np.sin, np.cos)]
    )


# Contiguous folds over phase order. Metrics are descriptive exploratory comparisons.
folds = np.array_split(np.arange(len(scan)), 5)
models = {
    "constant": lambda train, test: (np.ones((len(train), 1)), np.ones((len(test), 1))),
    "Fourier k=1..3": lambda train, test: (
        fourier_features(phi[train]),
        fourier_features(phi[test]),
    ),
    "order trend": lambda train, test: (
        (train / max(len(scan) - 1, 1)).reshape(-1, 1),
        (test / max(len(scan) - 1, 1)).reshape(-1, 1),
    ),
}
print("\nContiguous phase-block cross-validation (RMSE, R2):")
for j, name in enumerate(stokes):
    y = y_all[:, j]
    for model_name, features in models.items():
        pred = np.full(len(scan), np.nan)
        for test in folds:
            train = np.setdiff1d(np.arange(len(scan)), test)
            x_train, x_test = features(train, test)
            model = LinearRegression().fit(x_train, y[train])
            pred[test] = model.predict(x_test)
        print(
            f"{name:>2} | {model_name:<14} RMSE={mean_squared_error(y, pred)**0.5:.6f} "
            f"R2={r2_score(y, pred):.6f}"
        )

# Fit on all observations for visualization only.
fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
for j, name in enumerate(stokes):
    ax = axes.flat[j]
    ax.plot(phi, y_all[:, j], "o", ms=3, label="observed")
    grid = np.linspace(phi.min(), phi.max(), 500)
    fit = LinearRegression().fit(fourier_features(phi), y_all[:, j])
    ax.plot(grid, fit.predict(fourier_features(grid)), lw=1.5, label="Fourier k=1..3")
    ax.set(xlabel="Mean phase (rad)", ylabel=name)
    ax.legend(frameon=False)
axes.flat[3].plot(phi, norm2, "o-", ms=3, label="S1^2 + S2^2 + S3^2")
if dop_col:
    ax2 = axes.flat[3].twinx()
    ax2.plot(phi, scan[dop_col], color="tab:red", alpha=0.7, label="exported DOP")
    ax2.set_ylabel("Exported DOP (native scale)")
axes.flat[3].set(xlabel="Mean phase (rad)", ylabel="Stokes squared norm")
fig.suptitle("Supplied mean-phase scan: descriptive fits, not independent repeats")
plt.savefig("mean_phase_analysis.png", dpi=160)
print("\nSaved visualization: mean_phase_analysis.png")
plt.show()
