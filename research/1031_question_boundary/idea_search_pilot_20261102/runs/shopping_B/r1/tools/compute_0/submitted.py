import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.metrics import log_loss

raw = TABLES['main'].copy()
dur = ['Administrative_Duration', 'Informational_Duration', 'ProductRelated_Duration']
raw['total_duration'] = raw[dur].sum(axis=1)
raw['zero_total_duration'] = (raw['total_duration'] == 0).astype(int)
raw['product_share'] = np.divide(raw['ProductRelated_Duration'], raw['total_duration'], out=np.zeros(len(raw), dtype=float), where=raw['total_duration'].to_numpy() > 0)
raw['share_x_product_count'] = raw['product_share'] * raw['ProductRelated']
y = raw['Revenue'].astype(int).to_numpy()
num0 = ['Administrative', 'Informational', 'ProductRelated', 'total_duration']
num1 = num0 + ['product_share', 'share_x_product_count']
cat = ['Month', 'Weekend', 'VisitorType', 'OperatingSystems', 'Browser', 'Region', 'TrafficType', 'SpecialDay']

def model(num):
    prep = ColumnTransformer([('num', StandardScaler(), num), ('cat', OneHotEncoder(handle_unknown='ignore'), cat)])
    return make_pipeline(prep, LogisticRegression(max_iter=1000))

cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=20261102)
rows = []
for tr, te in cv.split(raw, y):
    b, a = model(num0), model(num1)
    b.fit(raw.iloc[tr], y[tr]); a.fit(raw.iloc[tr], y[tr])
    pb = b.predict_proba(raw.iloc[te])[:, 1]
    pa = a.predict_proba(raw.iloc[te])[:, 1]
    delta = log_loss(y[te], pb, labels=[0, 1]) - log_loss(y[te], pa, labels=[0, 1])
    train = raw.iloc[tr]
    q25, q75 = train.loc[train['total_duration'] > 0, 'product_share'].quantile([0.25, 0.75]).to_numpy()
    med_count = train['ProductRelated'].median()
    valid = raw.iloc[te].loc[raw.iloc[te]['total_duration'] > 0].copy()
    lo, hi = valid.copy(), valid.copy()
    lo['product_share'] = q25; hi['product_share'] = q75
    lo['share_x_product_count'] = q25 * med_count; hi['share_x_product_count'] = q75 * med_count
    contrast = float(np.mean(a.predict_proba(hi)[:, 1] - a.predict_proba(lo)[:, 1])) if len(valid) else None
    rows.append({'logloss_improvement': float(delta), 'share_q25': float(q25), 'share_q75': float(q75), 'median_product_count': float(med_count), 'modeled_probability_contrast': contrast})
print(__import__('json').dumps({'n': len(raw), 'zero_total_n': int(raw['zero_total_duration'].sum()), 'zero_total_fraction': float(raw['zero_total_duration'].mean()), 'folds': rows}, separators=(',', ':')))