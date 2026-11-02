import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/cross_domain_idea_probe_20261102/sources/uci_320_data.csv')
TABLES={"main":DF}
import json
import math
import pandas as pd
from scipy.stats import t

d = DF.loc[:, ['G1', 'G2', 'absences', 'traveltime']].copy()
d['eligible'] = d['G1'] < 10
d['high_absence'] = d['absences'] >= 6
d['change'] = d['G2'] - d['G1']
rows = []
for high in (False, True):
    for travel in (1, 2, 3, 4):
        g = d[(d['eligible']) & (d['high_absence'] == high) & (d['traveltime'] == travel)]
        n = int(len(g))
        mean = float(g['change'].mean()) if n else None
        if n >= 2:
            se = float(g['change'].std(ddof=1) / math.sqrt(n))
            half = float(t.ppf(0.975, n - 1) * se)
            ci = [mean - half, mean + half]
        else:
            ci = None
        rows.append({'high_absence': high, 'traveltime_category': travel, 'n': n, 'mean_G2_minus_G1': mean, 'ci95_t': ci})
print(json.dumps({'provisional_rules': {'G1_lt': 10, 'absences_gte': 6}, 'eligible_n': int(d['eligible'].sum()), 'strata': rows}, separators=(',', ':'), allow_nan=False))