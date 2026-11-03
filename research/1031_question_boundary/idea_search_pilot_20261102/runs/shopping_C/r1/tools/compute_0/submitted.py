import json
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score

df = TABLES['main'].copy()
y = df['Revenue'].astype(int)
base = df.drop(columns=['Revenue'])
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=2026)
results = {}
for name, cols in [('pagevalues_only', ['PageValues']), ('full', list(base.columns)), ('no_pagevalues', [c for c in base.columns if c != 'PageValues'])]:
    X = base[cols]
    cat = [c for c in cols if str(X[c].dtype) in ('object', 'bool', 'category', 'str')]
    num = [c for c in cols if c not in cat]
    prep = ColumnTransformer([('num', StandardScaler(), num), ('cat', OneHotEncoder(handle_unknown='ignore'), cat)])
    rows = []
    for fold, (tr, te) in enumerate(skf.split(X, y), 1):
        model = make_pipeline(prep, LogisticRegression(max_iter=1000))
        model.fit(X.iloc[tr], y.iloc[tr])
        p = model.predict_proba(X.iloc[te])[:, 1]
        rows.append({'fold': fold, 'average_precision': float(average_precision_score(y.iloc[te], p)), 'log_loss': float(log_loss(y.iloc[te], p)), 'roc_auc': float(roc_auc_score(y.iloc[te], p))})
    results[name] = rows
paired = []
for i in range(5):
    f, n = results['full'][i], results['no_pagevalues'][i]
    paired.append({'fold': i + 1, 'average_precision_full_minus_no_pagevalues': f['average_precision'] - n['average_precision'], 'log_loss_no_pagevalues_minus_full': n['log_loss'] - f['log_loss'], 'roc_auc_full_minus_no_pagevalues': f['roc_auc'] - n['roc_auc']})
print(json.dumps({'fold_metrics': results, 'paired_full_vs_no_pagevalues': paired}, separators=(',', ':')))