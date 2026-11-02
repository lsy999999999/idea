import json
import numpy as np
import pandas as pd

d = DF.copy()
d['high_abs'] = (d['absences'] >= 3).astype(float)
d['sup'] = (d['schoolsup'] == 'yes').astype(float)
d['gain'] = d['G2'] - d['G1']
X = pd.DataFrame({
    'intercept': np.ones(len(d)),
    'sup': d['sup'],
    'high_abs': d['high_abs'],
    'sup_x_high': d['sup'] * d['high_abs'],
    'G1': d['G1'].astype(float),
    'failures': d['failures'].astype(float),
    'studytime': d['studytime'].astype(float),
    'age': d['age'].astype(float)
})
X = pd.concat([X, pd.get_dummies(d['school'], drop_first=True, dtype=float)], axis=1)
A = X.to_numpy(dtype=float)
y = d['gain'].to_numpy(dtype=float)
beta = np.linalg.lstsq(A, y, rcond=None)[0]
resid = y - A @ beta
bread = np.linalg.pinv(A.T @ A)
h = np.einsum('ij,jk,ik->i', A, bread, A)
adj = resid / np.maximum(1.0 - h, 1e-12)
meat = (A.T * (adj ** 2)) @ A
cov = bread @ meat @ bread
j = list(X.columns).index('sup_x_high')
est = float(beta[j])
se = float(np.sqrt(max(cov[j, j], 0.0)))
cells = {}
for hi, hlabel in [(0.0, 'abs_lt_3'), (1.0, 'abs_ge_3')]:
    for su, slabel in [(0.0, 'support_no'), (1.0, 'support_yes')]:
        cells[hlabel + '_' + slabel] = int(((d['high_abs'] == hi) & (d['sup'] == su)).sum())
print(json.dumps({
    'n': int(len(d)),
    'cells': cells,
    'interaction_grade_points': est,
    'hc3_se': se,
    'ci95_normal': [est - 1.96 * se, est + 1.96 * se],
    'design_rank': int(np.linalg.matrix_rank(A)),
    'design_columns': int(A.shape[1]),
    'interpretation': 'descriptive_conditional_association_only_unknown_timing_and_confounding'
}, separators=(',', ':')))