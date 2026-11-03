import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/idea_search_pilot_20261102/setup/uci468.csv')
TABLES={"main":DF}
import json
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
raw['SpecialDay_level'] = raw['SpecialDay'].astype(str)
y = raw['Revenue'].astype(int).to_numpy()
num = ['Administrative', 'Informational', 'ProductRelated', 'total_duration', 'BounceRates', 'ExitRates']
cat = ['Month', 'Weekend', 'VisitorType', 'OperatingSystems', 'Browser', 'Region', 'TrafficType']

def model(add_specialday):
    cats = cat + (['SpecialDay_level'] if add_specialday else [])
    prep = ColumnTransformer([('num', StandardScaler(), num), ('cat', OneHotEncoder(handle_unknown='ignore'), cats)])
    return make_pipeline(prep, LogisticRegression(max_iter=1000))

cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=20261102)
folds = []
for split_id, (tr, te) in enumerate(cv.split(raw, y)):
    base, aug = model(False), model(True)
    base.fit(raw.iloc[tr], y[tr]); aug.fit(raw.iloc[tr], y[tr])
    lb = log_loss(y[te], base.predict_proba(raw.iloc[te])[:, 1], labels=[0, 1])
    la = log_loss(y[te], aug.predict_proba(raw.iloc[te])[:, 1], labels=[0, 1])
    folds.append({'repeat': split_id // 5, 'fold': split_id % 5, 'improvement': float(lb - la)})
repeat_means = [{'repeat': r, 'mean_improvement': float(np.mean([f['improvement'] for f in folds if f['repeat'] == r]))} for r in range(3)]
level_counts = {str(k): int(v) for k, v in raw['SpecialDay_level'].value_counts().sort_index().items()}
month_level_counts = {str(m): {str(k): int(v) for k, v in g['SpecialDay_level'].value_counts().sort_index().items()} for m, g in raw.groupby('Month', sort=True)}
print(json.dumps({'n': len(raw), 'level_counts': level_counts, 'month_level_counts': month_level_counts, 'folds': folds, 'repeat_means': repeat_means}, separators=(',', ':')))