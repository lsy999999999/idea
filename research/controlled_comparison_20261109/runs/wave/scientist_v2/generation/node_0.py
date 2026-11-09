import os

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["NUMEXPR_NUM_THREADS"] = "4"

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import pearsonr
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, SplineTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

FILE = "measurements.csv"
df = pd.read_csv(FILE)
required = ["time_s", "correlation_width", "mean_shear_magnitude"]
missing_cols = set(required) - set(df.columns)
if missing_cols:
    raise ValueError(f"Missing required columns: {sorted(missing_cols)}")
df = (
    df[required]
    .apply(pd.to_numeric, errors="coerce")
    .dropna()
    .sort_values("time_s")
    .reset_index(drop=True)
)
if len(df) < 100:
    raise ValueError(f"Too few valid rows: {len(df)}")

t = df.time_s.to_numpy()
w = df.correlation_width.to_numpy()
y = df.mean_shear_magnitude.to_numpy()
dt = np.diff(t)
step = float(np.median(dt[dt > 0]))
print(
    f"rows={len(df)} duplicate_times={int(df.time_s.duplicated().sum())} "
    f"missing_after_cleaning=0 median_dt_s={step:.6g} "
    f"regularity_cv={np.std(dt)/np.mean(dt):.5g}"
)
print(
    f"time_range_s=({t.min():.4f}, {t.max():.4f}) "
    f"width_range=({w.min():.4f}, {w.max():.4f}) "
    f"shear_range=({y.min():.5f}, {y.max():.5f})"
)
print(
    f"width_shear_pearson_r={pearsonr(w, y).statistic:.4f} (descriptive, serial samples)"
)


def features(width, time, delta=None):
    base = np.column_stack([time, width])
    if delta is not None:
        base = np.column_stack([base, delta, np.sign(delta), width * np.sign(delta)])
    return base


# Approximate smooth nonlinear dependence with low-complexity splines, standardized ridge.
def model():
    return make_pipeline(
        StandardScaler(),
        SplineTransformer(n_knots=4, degree=2, include_bias=False),
        Ridge(alpha=2.0),
    )


def blocked_scores(X, y):
    splitter = TimeSeriesSplit(n_splits=5)
    pred = np.full(len(y), np.nan)
    for train, test in splitter.split(X):
        m = model()
        m.fit(X[train], y[train])
        pred[test] = m.predict(X[test])
    valid = np.isfinite(pred)
    return (
        mean_squared_error(y[valid], pred[valid]) ** 0.5,
        mean_absolute_error(y[valid], pred[valid]),
        pred,
        valid,
    )


# Leave early rows unavailable until lagged differences can be calculated.
def lag_delta(seconds):
    k = max(1, int(round(seconds / step)))
    delta = np.full(len(w), np.nan)
    delta[k:] = w[k:] - w[:-k]
    return delta, k


dprimary, kprimary = lag_delta(0.1)
valid0 = np.arange(len(y)) >= kprimary
X_time = features(w, t)
X_width_time = features(w, t)
X_aug = features(w, t, np.nan_to_num(dprimary, nan=0.0))

# Common evaluation interval across all models.
ids = np.flatnonzero(valid0)
yt = y[ids]
results = {}
for name, X in [("time_width", X_width_time), ("time_width_lag", X_aug)]:
    rmse, mae, pred, valid = blocked_scores(X[ids], yt)
    results[name] = (rmse, mae, pred, valid)
    print(f"blocked_{name}: RMSE={rmse:.7g} MAE={mae:.7g} n_test={valid.sum()}")


# Time-only alternative, using a univariate smooth predictor.
def time_only_scores(time, target):
    X = time.reshape(-1, 1)
    return blocked_scores(X, target)


rmse, mae, _, _ = time_only_scores(t[ids], yt)
print(f"blocked_time_only: RMSE={rmse:.7g} MAE={mae:.7g}")

# Sensitivity to prespecified lag windows; same model and same blocked scheme.
for lag_s in (0.05, 0.1, 0.2):
    d, k = lag_delta(lag_s)
    use = np.arange(len(y)) >= k
    X = features(w, t, np.nan_to_num(d, nan=0.0))
    rm, ma, _, _ = blocked_scores(X[use], y[use])
    print(f"lag_s={lag_s:.2f} samples={k} blocked_RMSE={rm:.7g} MAE={ma:.7g}")

# Fit augmented model to all usable points for residual dependence and descriptive contrast.
use = np.arange(len(y)) >= kprimary
fit = model()
fit.fit(X_aug[use], y[use])
resid = y[use] - fit.predict(X_aug[use])


def acf1(x):
    return float(np.corrcoef(x[:-1], x[1:])[0, 1]) if len(x) > 2 else np.nan


print(f"augmented_in_sample_residual_acf1={acf1(resid):.4f}")

# Growth/decline contrast within common width support, using adjacent changes.
direction = np.sign(dprimary)
lo, hi = np.nanpercentile(w[use], [10, 90])
inside = use & (w >= lo) & (w <= hi) & (direction != 0)
g = y[inside & (direction > 0)]
s = y[inside & (direction < 0)]
contrast = float(np.mean(g) - np.mean(s)) if len(g) and len(s) else np.nan
print(
    f"matched_support_width=({lo:.4f},{hi:.4f}) growth_n={len(g)} decline_n={len(s)} "
    f"raw_shear_contrast_growth_minus_decline={contrast:.7g}"
)

# Moving-block bootstrap for the descriptive matched contrast, preserving local sequence.
rng = np.random.default_rng(17)
idx = np.flatnonzero(inside)
block = max(1, int(round(0.1 / step)))
boot = []
if len(idx) > 2 * block and len(g) and len(s):
    for _ in range(500):
        sampled = []
        while len(sampled) < len(idx):
            start = rng.integers(0, max(1, len(idx) - block + 1))
            sampled.extend(idx[start : start + block])
        sampled = np.asarray(sampled[: len(idx)])
        gd = sampled[direction[sampled] > 0]
        sd = sampled[direction[sampled] < 0]
        if len(gd) and len(sd):
            boot.append(np.mean(y[gd]) - np.mean(y[sd]))
if boot:
    print(
        f"block_bootstrap_contrast_95pct=({np.percentile(boot,2.5):.7g},"
        f"{np.percentile(boot,97.5):.7g}) block_samples={block} replicates={len(boot)}"
    )
else:
    print(
        "block_bootstrap_contrast_95pct=unavailable (insufficient directional coverage)"
    )

# Compact visualization of the observed aggregate and conditional scatter.
fig, ax = plt.subplots(2, 1, figsize=(9, 6), constrained_layout=True)
ax[0].plot(t, w, lw=1, label="correlation width")
ax[0].set_ylabel("Width")
ax[0].set_xlabel("Time (s)")
ax2 = ax[0].twinx()
ax2.plot(t, y, lw=1, color="tab:orange", label="mean shear")
ax2.set_ylabel("Mean shear")
ax[1].scatter(
    w[inside & (direction > 0)],
    y[inside & (direction > 0)],
    s=8,
    alpha=0.5,
    label="width increasing",
)
ax[1].scatter(
    w[inside & (direction < 0)],
    y[inside & (direction < 0)],
    s=8,
    alpha=0.5,
    label="width decreasing",
)
ax[1].set_xlabel("Correlation width")
ax[1].set_ylabel("Mean shear")
ax[1].legend()
fig.savefig("coarsening_shear_memory.png", dpi=160)
print("plot_saved=coarsening_shear_memory.png")
