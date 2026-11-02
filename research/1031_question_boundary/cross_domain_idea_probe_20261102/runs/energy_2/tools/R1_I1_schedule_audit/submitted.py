import json
import numpy as np
import pandas as pd

d = DF[['date', 'Appliances']].copy()
d['ts'] = pd.to_datetime(d['date'], format='%Y-%m-%d%H:%M:%S')
d = d.sort_values('ts').reset_index(drop=True)
cut = int(len(d) * 0.60)
cal = d.iloc[:cut].copy()
test = d.iloc[cut:].copy()
threshold = float(cal['Appliances'].quantile(0.90))
d['trigger_next'] = d['Appliances'].shift(1).ge(threshold).fillna(False)
test['trigger'] = d.loc[test.index, 'trigger_next'].to_numpy()
test['high'] = test['Appliances'].ge(threshold)
test['week'] = test['ts'].dt.strftime('%G-%V')
test['hour'] = test['ts'].dt.hour
trigger = test[test['trigger']]
strata = [(key, len(g)) for key, g in trigger.groupby(['week', 'hour'], sort=True)]
rng = np.random.default_rng(20261102)
draw_means = []
matched_slots = 0
for key, n_slots in strata:
    pool_mask = (test['week'].eq(key[0]) & test['hour'].eq(key[1]))
    pool = test.loc[pool_mask]
    matched_slots += min(n_slots, len(pool))
for _ in range(200):
    chosen = []
    for key, n_slots in strata:
        pool_mask = (test['week'].eq(key[0]) & test['hour'].eq(key[1]))
        pool = test.loc[pool_mask]
        n = min(n_slots, len(pool))
        if n:
            chosen.extend(rng.choice(pool.index.to_numpy(), size=n, replace=False).tolist())
    sample = test.loc[chosen]
    draw_means.append(float(sample['high'].mean()) if len(sample) else None)
out = {
    'calibration_rows': int(len(cal)),
    'heldout_rows': int(len(test)),
    'threshold_wh_per_10min': threshold,
    'trigger_slots': int(len(trigger)),
    'trigger_high_share': float(trigger['high'].mean()) if len(trigger) else None,
    'matched_random_slots_per_draw': int(matched_slots),
    'matched_random_high_share_mean_200_draws': float(np.mean([x for x in draw_means if x is not None])) if any(x is not None for x in draw_means) else None,
    'random_draws': 200,
    'interpretation': 'Aggregate schedule feasibility only; no circuit labels or causal savings.'
}
print(json.dumps(out, separators=(',', ':')))