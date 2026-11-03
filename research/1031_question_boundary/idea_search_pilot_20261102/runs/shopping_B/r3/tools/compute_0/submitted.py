import json
import numpy as np
import pandas as pd

raw = TABLES['main'].copy()
x = raw['ProductRelated'].to_numpy(dtype=float)
y = raw['Revenue'].astype(int).to_numpy()
ctx = ['VisitorType', 'TrafficType', 'Month', 'Weekend']
codes, uniques = pd.factorize(pd.MultiIndex.from_frame(raw[ctx]), sort=False)
n_cells = len(uniques)

def estimate(idx):
    xx, yy, cc = x[idx], y[idx], codes[idx]
    q25, q75 = np.quantile(xx, [0.25, 0.75])
    grp = np.where(xx <= q25, 0, np.where(xx >= q75, 1, -1))
    keep = grp >= 0
    grp, yy, cc = grp[keep], yy[keep], cc[keep]
    # Flatten cell/group pairs for vectorized counts and outcome sums.
    key = cc * 2 + grp
    count = np.bincount(key, minlength=n_cells * 2).reshape(n_cells, 2)
    wins = np.bincount(key, weights=yy, minlength=n_cells * 2).reshape(n_cells, 2)
    rates = np.divide(wins, count, out=np.zeros_like(wins), where=count > 0)
    shared = (count[:, 0] > 0) & (count[:, 1] > 0)
    weights = count[shared].sum(axis=1).astype(float)
    weights /= weights.sum() if weights.sum() else 1.0
    std = float(np.sum(weights * (rates[shared, 1] - rates[shared, 0]))) if shared.any() else np.nan
    marginal = float(yy[grp == 1].mean() - yy[grp == 0].mean()) if (grp == 0).any() and (grp == 1).any() else np.nan
    excluded = float(count[~shared].sum() / count.sum()) if count.sum() else np.nan
    return {'q25': float(q25), 'q75': float(q75), 'n_low': int((grp == 0).sum()), 'n_high': int((grp == 1).sum()), 'rate_low': float(yy[grp == 0].mean()), 'rate_high': float(yy[grp == 1].mean()), 'marginal': marginal, 'standardized': std, 'n_shared_cells': int(shared.sum()), 'n_nonshared_cells': int((~shared).sum()), 'fraction_group_sessions_excluded': excluded}

base = estimate(np.arange(len(raw)))
rng = np.random.default_rng(20261102)
boots = []
for _ in range(300):
    b = estimate(rng.integers(0, len(raw), len(raw)))
    if np.isfinite(b['marginal']) and np.isfinite(b['standardized']):
        boots.append([b['marginal'], b['standardized']])
arr = np.asarray(boots)
ci = np.quantile(arr, [0.025, 0.975], axis=0).tolist() if len(arr) else None
print(json.dumps({'n': len(raw), 'point_estimates': base, 'bootstrap_replicates_requested': 300, 'bootstrap_replicates_valid': len(boots), 'ci95_marginal_then_standardized': ci}, separators=(',', ':')))