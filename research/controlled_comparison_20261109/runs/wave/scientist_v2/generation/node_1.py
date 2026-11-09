import os

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["NUMEXPR_NUM_THREADS"] = "4"

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import SplineTransformer, StandardScaler, FunctionTransformer
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

FILE = "measurements.csv"
required = ["time_s", "correlation_width", "mean_shear_magnitude"]
df0 = pd.read_csv(FILE)
missing_cols = set(required) - set(df0.columns)
if missing_cols:
    raise ValueError(f"Missing required columns: {sorted(missing_cols)}")

raw = df0[required].apply(pd.to_numeric, errors="coerce")
print(
    f"input_rows={len(df0)} missing_required={int(raw.isna().any(axis=1).sum())} "
    f"duplicate_timestamps={int(raw.time_s.duplicated().sum())}"
)
df = (
    raw.dropna()
    .sort_values("time_s")
    .drop_duplicates("time_s", keep="first")
    .reset_index(drop=True)
)
if len(df) < 100:
    raise ValueError(f"Too few valid rows: {len(df)}")

t = df.time_s.to_numpy(float)
w = df.correlation_width.to_numpy(float)
y = df.mean_shear_magnitude.to_numpy(float)
dt = np.diff(t)
positive_dt = dt[dt > 0]
if len(positive_dt) == 0:
    raise ValueError("No increasing timestamps.")
step = float(np.median(positive_dt))
print(
    f"usable_rows={len(df)} time_range_s=({t.min():.4f},{t.max():.4f}) "
    f"median_dt_s={step:.7g} regularity_cv={np.std(dt)/np.mean(dt):.4g} "
    f"width_range=({w.min():.4f},{w.max():.4f}) "
    f"shear_range=({y.min():.5f},{y.max():.5f})"
)


def make_design(width, time, delta=None):
    # Spline only smooth state/time terms; preserve signed change and its direction
    # as explicit linear terms rather than transforming every column as a spline.
    parts = [width[:, None], time[:, None]]
    if delta is not None:
        direction = np.sign(delta)
        parts.extend([delta[:, None], direction[:, None], (width * direction)[:, None]])
    return np.column_stack(parts)


def fit_predict(train_x, train_y, test_x, spline_cols=2):
    # Each raw covariate is scaled, then spline-expanded consistently.
    prep = ColumnTransformer(
        [
            (
                "smooth",
                make_pipeline(
                    StandardScaler(),
                    SplineTransformer(n_knots=4, degree=2, include_bias=False),
                ),
                list(range(spline_cols)),
            )
        ]
        + [("linear", StandardScaler(), list(range(spline_cols, train_x.shape[1])))],
        remainder="drop",
    )
    model = make_pipeline(prep, Ridge(alpha=2.0))
    model.fit(train_x, train_y)
    return model, model.predict(test_x)


def blocked_scores(X, target):
    pred = np.full(len(target), np.nan)
    splitter = TimeSeriesSplit(n_splits=5)
    for train, test in splitter.split(X):
        _, pred[test] = fit_predict(X[train], target[train], X[test], spline_cols=2)
    valid = np.isfinite(pred)
    return (
        float(np.sqrt(mean_squared_error(target[valid], pred[valid]))),
        float(mean_absolute_error(target[valid], pred[valid])),
        pred,
        valid,
    )


def lag_delta(seconds):
    k = max(1, int(round(seconds / step)))
    delta = np.full(len(w), np.nan)
    delta[k:] = (w[k:] - w[:-k]) / (k * step)
    return delta, k


def report_score(name, X, target):
    rmse, mae, _, valid = blocked_scores(X, target)
    print(f"blocked_{name}: RMSE={rmse:.7g} MAE={mae:.7g} n_test={int(valid.sum())}")


# Use an identical evaluation interval for all models in the primary comparison.
primary_s = 0.10
dprimary, kprimary = lag_delta(primary_s)
ids = np.arange(kprimary, len(y))
yt = y[ids]
X_base = make_design(w, t)
X_aug = make_design(w, t, dprimary)
report_score("time_width", X_base[ids], yt)
report_score("time_width_lagged_change_direction", X_aug[ids], yt)
report_score("time_only", t[ids, None], yt)

for lag_s in (0.05, 0.10, 0.20):
    delta, k = lag_delta(lag_s)
    use = np.arange(k, len(y))
    X = make_design(w, t, delta)
    report_score(f"lag_{lag_s:.2f}s", X[use], y[use])

# Residual autocorrelation is reported to show remaining serial structure.
final_model, fitted = fit_predict(X_aug[ids], yt, X_aug[ids], spline_cols=2)
resid = yt - fitted
acf1 = float(np.corrcoef(resid[:-1], resid[1:])[0, 1])
print(f"augmented_in_sample_residual_acf1={acf1:.4f}")


# Compare direction-specific local linear smooths on their shared width support.
direction = np.sign(dprimary)
usable = np.arange(len(y)) >= kprimary
growing = usable & (direction > 0)
shrinking = usable & (direction < 0)
lo = max(np.quantile(w[growing], 0.05), np.quantile(w[shrinking], 0.05))
hi = min(np.quantile(w[growing], 0.95), np.quantile(w[shrinking], 0.95))
inside = usable & (w >= lo) & (w <= hi) & (direction != 0)
if lo >= hi or inside.sum() < 20:
    contrast = np.nan
    print("matched_width_contrast=unavailable (insufficient overlap)")
else:
    # Fit separate smooths; integrate their difference over observed shared-support widths.
    n_knots = 5
    sm = SplineTransformer(n_knots=n_knots, degree=2, include_bias=False)
    Xg = sm.fit_transform(w[growing, None])
    Xs = sm.fit_transform(w[shrinking, None])
    mg = Ridge(alpha=2.0).fit(Xg, y[growing])
    ms = Ridge(alpha=2.0).fit(Xs, y[shrinking])
    grid = np.linspace(lo, hi, 200)[:, None]
    contrast = float(
        np.mean(mg.predict(sm.transform(grid)) - ms.predict(sm.transform(grid)))
    )
    print(
        f"matched_width_support=({lo:.4f},{hi:.4f}) "
        f"growing_n={int((growing & (w >= lo) & (w <= hi)).sum())} "
        f"shrinking_n={int((shrinking & (w >= lo) & (w <= hi)).sum())} "
        f"smoothed_growth_minus_decline={contrast:.7g}"
    )

# Moving-block bootstrap on the complete chronological record, retaining contiguous blocks.
rng = np.random.default_rng(17)
block = max(1, int(round(0.10 / step)))
boot = []
if np.isfinite(contrast):
    for _ in range(500):
        starts = rng.integers(0, len(y) - block + 1, size=int(np.ceil(len(y) / block)))
        sample_idx = np.concatenate([np.arange(s, s + block) for s in starts])[: len(y)]
        dg = direction[sample_idx]
        ww = w[sample_idx]
        yy = y[sample_idx]
        keep = (ww >= lo) & (ww <= hi) & (dg != 0)
        if np.sum(keep & (dg > 0)) < 10 or np.sum(keep & (dg < 0)) < 10:
            continue
        # Bootstrap descriptive raw matched-support contrast; blocks are genuinely contiguous.
        gmask = keep & (dg > 0)
        smask = keep & (dg < 0)
        boot.append(float(np.mean(yy[gmask]) - np.mean(yy[smask])))
if len(boot) >= 50:
    print(
        f"contiguous_block_bootstrap_raw_contrast_95pct="
        f"({np.percentile(boot, 2.5):.7g},{np.percentile(boot, 97.5):.7g}) "
        f"block_samples={block} valid_replicates={len(boot)}"
    )
else:
    print(
        "contiguous_block_bootstrap_95pct=unavailable (insufficient directional coverage)"
    )

fig, ax = plt.subplots(2, 1, figsize=(9, 6), constrained_layout=True)
ax[0].plot(t, w, lw=1, label="correlation width")
ax[0].set_ylabel("Correlation width")
ax[0].set_xlabel("Time (s)")
ax2 = ax[0].twinx()
ax2.plot(t, y, lw=1, color="tab:orange", label="mean shear")
ax2.set_ylabel("Mean shear magnitude")
ax[1].scatter(
    w[inside & (direction > 0)],
    y[inside & (direction > 0)],
    s=8,
    alpha=0.45,
    label="width increasing",
)
ax[1].scatter(
    w[inside & (direction < 0)],
    y[inside & (direction < 0)],
    s=8,
    alpha=0.45,
    label="width decreasing",
)
ax[1].set_xlabel("Correlation width")
ax[1].set_ylabel("Mean shear magnitude")
ax[1].legend()
fig.savefig("coarsening_shear_memory.png", dpi=160)
print("plot_saved=coarsening_shear_memory.png")
print(
    "interpretation=descriptive single aggregate; lagged prediction or directional "
    "contrast does not establish independent replication or a causal memory mechanism"
)
