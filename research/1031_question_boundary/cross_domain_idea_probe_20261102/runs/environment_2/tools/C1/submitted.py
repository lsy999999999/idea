import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import brier_score_loss, log_loss

d = DF.sort_values('No').reset_index(drop=True).copy()
d['pm2.5'] = pd.to_numeric(d['pm2.5'], errors='coerce')
rows = []
candidate = 0
censored = 0
for i in range(3, len(d) - 6):
    if not (d.loc[i, 'No'] == d.loc[i-1, 'No'] + 1 and d.loc[i-1, 'pm2.5'] < 150 and d.loc[i, 'pm2.5'] >= 150):
        continue
    if not all(d.loc[k, 'No'] == d.loc[k-1, 'No'] + 1 and pd.notna(d.loc[k, 'pm2.5']) for k in range(i-3, i+1)):
        continue
    candidate += 1
    outcome = None
    missing = False
    for h in range(1, 7):
        j = i + h
        if d.loc[j, 'No'] != d.loc[j-1, 'No'] + 1 or pd.isna(d.loc[j, 'pm2.5']):
            missing = True
            break
        if h >= 3 and all(d.loc[k, 'pm2.5'] < 75 for k in range(j-2, j+1)):
            outcome = 1
            break
    if outcome is None and not missing:
        outcome = 0
    if outcome is None:
        censored += 1
        continue
    rows.append({'year': int(d.loc[i, 'year']), 'month': int(d.loc[i, 'month']), 'hour': int(d.loc[i, 'hour']), 'pm0': float(d.loc[i, 'pm2.5']), 'lag1': float(d.loc[i-1, 'pm2.5']), 'lag2': float(d.loc[i-2, 'pm2.5']), 'lag3': float(d.loc[i-3, 'pm2.5']), 'Iws': float(d.loc[i, 'Iws']), 'transition': int(d.loc[i, 'cbwd'] != d.loc[i-1, 'cbwd']), 'clear': int(outcome)})
e = pd.DataFrame(rows)
result = {'candidate_entries_with_complete_history': int(candidate), 'censored_outcomes': int(censored), 'complete_entries': int(len(e))}
if len(e):
    result['by_transition'] = {str(int(x)): {'n': int(len(g)), 'clearances': int(g['clear'].sum()), 'rate': float(g['clear'].mean())} for x, g in e.groupby('transition')}
    base = pd.get_dummies(e[['pm0','lag1','lag2','lag3','Iws','month','hour']], columns=['month','hour'], dtype=float)
    aug = base.copy()
    aug['transition'] = e['transition'].to_numpy()
    oof = []
    folds = []
    for year in sorted(e['year'].unique()):
        tr = e['year'] != year
        te = ~tr
        if tr.sum() < 10 or e.loc[tr, 'clear'].nunique() < 2 or e.loc[te, 'clear'].nunique() < 1:
            folds.append({'year': int(year), 'status': 'skipped_insufficient_training_or_test_class'})
            continue
        models = []
        probs = []
        for x in (base, aug):
            model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
            model.fit(x.loc[tr], e.loc[tr, 'clear'])
            p = model.predict_proba(x.loc[te])[:, 1]
            probs.append(p)
        m1 = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
        m1.fit(aug.loc[tr], e.loc[tr, 'clear'])
        flip0 = aug.loc[te].copy()
        flip1 = aug.loc[te].copy()
        flip0['transition'] = 0
        flip1['transition'] = 1
        risk_increment = float(np.mean(m1.predict_proba(flip1)[:,1] - m1.predict_proba(flip0)[:,1]))
        y = e.loc[te, 'clear'].to_numpy()
        folds.append({'year': int(year), 'n': int(te.sum()), 'standardized_risk_increment': risk_increment, 'brier_base': float(brier_score_loss(y, probs[0])), 'brier_augmented': float(brier_score_loss(y, probs[1])), 'logloss_base': float(log_loss(y, probs[0], labels=[0,1])), 'logloss_augmented': float(log_loss(y, probs[1], labels=[0,1]))})
        oof.extend([{'y': int(yy), 'p_base': float(pb), 'p_augmented': float(pa)} for yy, pb, pa in zip(y, probs[0], probs[1])])
    result['folds'] = folds
    if oof:
        y = np.array([r['y'] for r in oof])
        pb = np.array([r['p_base'] for r in oof])
        pa = np.array([r['p_augmented'] for r in oof])
        result['pooled_oof'] = {'n': int(len(oof)), 'brier_base': float(brier_score_loss(y, pb)), 'brier_augmented': float(brier_score_loss(y, pa)), 'logloss_base': float(log_loss(y, pb, labels=[0,1])), 'logloss_augmented': float(log_loss(y, pa, labels=[0,1]))}
print(json.dumps(result, separators=(',', ':'), allow_nan=False))