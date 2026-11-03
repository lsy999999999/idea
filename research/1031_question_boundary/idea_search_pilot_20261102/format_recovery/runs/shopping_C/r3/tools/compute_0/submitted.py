import json
import numpy as np
import pandas as pd

df = TABLES['main'].copy()
cols = ['Administrative_Duration', 'Informational_Duration', 'ProductRelated_Duration']
total = df[cols].sum(axis=1)
valid = total > 0
x = df.loc[valid].copy()
x['total_duration'] = total.loc[valid]
x['product_share'] = x['ProductRelated_Duration'] / x['total_duration']
y = x['Revenue'].astype(int)
quantiles = [0, .1, .25, .5, .75, .9, 1]
by_revenue = {}
for label, group in x.groupby('Revenue', observed=True):
    by_revenue[str(label)] = {'n': int(len(group)), 'share_quantiles': {str(q): float(group['product_share'].quantile(q)) for q in quantiles}}
x['share_decile'] = pd.qcut(x['product_share'].rank(method='first'), 10, labels=False)
deciles = x.groupby('share_decile', observed=True).agg(n=('Revenue', 'size'), conversions=('Revenue', 'sum'), rate=('Revenue', 'mean')).reset_index().to_dict(orient='records')
correlations = {c: float(x['product_share'].corr(x[c])) for c in ['total_duration', 'Administrative', 'Informational', 'ProductRelated']}
print(json.dumps({'n_total': int(len(df)), 'n_zero_total_duration': int((~valid).sum()), 'n_included': int(valid.sum()), 'included_by_revenue': {str(k): int(v) for k, v in x['Revenue'].value_counts().items()}, 'share_quantiles_by_revenue': by_revenue, 'share_deciles': deciles, 'share_correlations': correlations, 'month_counts': x['Month'].value_counts().to_dict(), 'visitor_type_counts': x['VisitorType'].value_counts().to_dict(), 'traffic_type_counts': x['TrafficType'].value_counts().to_dict()}, separators=(',', ':')))