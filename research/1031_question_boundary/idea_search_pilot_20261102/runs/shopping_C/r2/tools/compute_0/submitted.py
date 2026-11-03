import json
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression

df = TABLES['main'].copy()
df['Revenue'] = df['Revenue'].astype(int)
df['SpecialDay'] = df['SpecialDay'].astype(str)
counts = df.groupby(['Month', 'SpecialDay'], observed=True).agg(n=('Revenue', 'size'), conversions=('Revenue', 'sum'), rate=('Revenue', 'mean')).reset_index()
features = df.drop(columns=['Revenue', 'PageValues'])
y = df['Revenue']
cat = [c for c in features.columns if str(features[c].dtype) in ('object', 'bool', 'category', 'str')]
num = [c for c in features.columns if c not in cat]
prep = ColumnTransformer([('num', StandardScaler(), num), ('cat', OneHotEncoder(handle_unknown='ignore'), cat)])
model = make_pipeline(prep, LogisticRegression(max_iter=1000))
model.fit(features, y)
base = features.copy()
margins = {}
for score in sorted(features['SpecialDay'].unique(), key=float):
    cf = base.copy()
    cf['SpecialDay'] = score
    margins[score] = float(model.predict_proba(cf)[:, 1].mean())
ref = margins.get('0.0', margins.get('0'))
print(json.dumps({'cells': counts.to_dict(orient='records'), 'sparse_or_empty_cells': [{'Month': m, 'SpecialDay': s, 'n': n} for m, s, n in [(m, s, int(n)) for m in sorted(df['Month'].unique()) for s in sorted(df['SpecialDay'].unique(), key=float) for n in [int(((df['Month'] == m) & (df['SpecialDay'] == s)).sum())]] if n < 20], 'standardized_mean_predicted_rates': margins, 'differences_vs_zero': {s: v - ref for s, v in margins.items()}}, separators=(',', ':')))