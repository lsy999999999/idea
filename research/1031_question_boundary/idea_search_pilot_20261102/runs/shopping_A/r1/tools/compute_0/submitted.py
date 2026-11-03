import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize

x = DF.loc[(DF['ProductRelated'] > 0) & DF['VisitorType'].isin(['New_Visitor', 'Returning_Visitor'])].copy().reset_index(drop=True)
y = x['Revenue'].astype(int).to_numpy()
new = (x['VisitorType'].to_numpy() == 'New_Visitor').astype(float)
dwell = np.log1p((x['ProductRelated_Duration'] / x['ProductRelated']).to_numpy(dtype=float))
count = np.log1p(x['ProductRelated'].to_numpy(dtype=float))
months = pd.get_dummies(x['Month'], drop_first=True, dtype=float).to_numpy()

def design(d):
    z = (d - d.mean()) / (d.std() or 1.0)
    return np.column_stack([np.ones(len(z)), z, new, z * new, count, months])

def fit(X, yy):
    def objective(b):
        eta = np.clip(X @ b, -30, 30)
        return np.logaddexp(0, eta).sum() - yy @ eta + 1e-6 * (b @ b)
    result = minimize(objective, np.zeros(X.shape[1]), method='L-BFGS-B')
    return result.x if result.success else None

X = design(dwell)
b = fit(X, y)
counts = x.groupby(['VisitorType', 'Revenue']).size().unstack(fill_value=0).to_dict(orient='index')
rng = np.random.default_rng(20261102)
boot = []
for _ in range(300):
    idx = rng.integers(0, len(y), len(y))
    if len(np.unique(y[idx])) < 2:
        continue
    bb = fit(X[idx], y[idx])
    if bb is not None:
        boot.append(float(bb[3]))
q99 = float(np.quantile(dwell, .99))
cap = np.minimum(dwell, q99)
bcap = fit(design(cap), y)
print(json.dumps({'n':len(x),'counts':counts,'interaction_log_odds':None if b is None else float(b[3]),'bootstrap_95_ci':None if len(boot)<30 else [float(v) for v in np.quantile(boot,[.025,.975])],'bootstrap_successes':len(boot),'winsor99_interaction_log_odds':None if bcap is None else float(bcap[3])},separators=(',',':')))