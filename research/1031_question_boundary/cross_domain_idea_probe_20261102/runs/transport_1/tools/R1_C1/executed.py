import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/cross_domain_idea_probe_20261102/sources/uci_275_data.csv')
TABLES={"main":DF}
import json
import numpy as np
import pandas as pd

d = DF.loc[(DF['workingday'] == 0) & DF['hr'].between(9, 17) & DF['weathersit'].isin([1, 2, 3]), ['dteday', 'season', 'hr', 'weathersit', 'casual', 'registered']].copy()
d['wx'] = np.where(d['weathersit'].eq(1), 1, 2)
d['day'] = d['dteday'].astype(str)
keys = ['season', 'hr']
full = d.groupby(keys + ['wx'])[['casual', 'registered']].agg(['mean', 'size'])
strata = sorted(set((int(a), int(b)) for a, b in d[keys].drop_duplicates().itertuples(index=False, name=None) if (a, b, 1) in full.index and (a, b, 2) in full.index))
if not strata:
    raise ValueError('No season-hour strata contain both exposure groups')
def estimate(frame):
    g = frame.groupby(keys + ['wx'])[['casual', 'registered']].mean()
    out = {}
    for y in ['casual', 'registered']:
        p = g[y].unstack('wx').reindex(pd.MultiIndex.from_tuples(strata, names=keys))
        if p[[1, 2]].isna().any().any():
            return None
        out[y] = float(np.log((p[2] + 0.5) / (p[1] + 0.5)).mean())
    return {'casual_log_ratio': out['casual'], 'registered_log_ratio': out['registered'], 'contrast': out['casual'] - out['registered']}
point = estimate(d)
rng = np.random.default_rng(275)
days = d['day'].unique()
boots = []
for _ in range(500):
    sampled = rng.choice(days, size=len(days), replace=True)
    weights = pd.Series(sampled).value_counts()
    b = d.copy()
    b['_w'] = b['day'].map(weights).fillna(0)
    b = b.loc[b['_w'] > 0].copy()
    # Duplicate sampled dates are represented by row weights in weighted means.
    rows = []
    for (s, h, wx), g in b.groupby(keys + ['wx']):
        w = g['_w'].to_numpy()
        rows.append((s, h, wx, np.average(g['casual'], weights=w), np.average(g['registered'], weights=w)))
    agg = pd.DataFrame(rows, columns=keys + ['wx', 'casual', 'registered'])
    z = estimate(agg)
    if z is not None:
        boots.append(z['contrast'])
if not boots:
    raise ValueError('No bootstrap replicate retained all eligible strata')
result = {'estimand': 'equal-season-hour average log mean-count ratio, categories 2-3 vs 1; casual minus registered', 'point': point, 'bootstrap_95_percentile_interval': [float(x) for x in np.quantile(boots, [0.025, 0.975])], 'bootstrap_replicates_valid': len(boots), 'eligible_strata': len(strata), 'support': {str(wx): {'rows': int((d['wx'] == wx).sum()), 'dates': int(d.loc[d['wx'] == wx, 'day'].nunique())} for wx in [1, 2]}}
print(json.dumps(result, separators=(',', ':')))