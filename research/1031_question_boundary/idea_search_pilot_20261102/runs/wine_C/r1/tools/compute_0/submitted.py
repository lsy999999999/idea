import json
import numpy as np
import pandas as pd

rows=[]
chem=['fixed_acidity','volatile_acidity','citric_acid','residual_sugar','chlorides','free_sulfur_dioxide','total_sulfur_dioxide','density','pH','sulphates','alcohol']
for color,g0 in DF.groupby('color'):
    g=g0.copy().reset_index(drop=True)
    x=np.log1p(g['residual_sugar'].astype(float).to_numpy())
    a=g['alcohol'].astype(float).to_numpy()
    x=(x-x.mean())/(x.std() or 1.0); a=(a-a.mean())/(a.std() or 1.0)
    cols=[np.ones(len(g)),a,x,a*x]
    for c in chem:
        if c not in ('alcohol','residual_sugar'):
            v=g[c].astype(float).to_numpy(); sd=v.std()
            cols.append((v-v.mean())/(sd if sd else 1.0))
    X=np.column_stack(cols); y=g['quality'].astype(float).to_numpy()
    beta=np.linalg.lstsq(X,y,rcond=None)[0]
    rng=np.random.default_rng(20261102); vals=[]
    for _ in range(300):
        ix=rng.integers(0,len(y),len(y))
        try: vals.append(float(np.linalg.lstsq(X[ix],y[ix],rcond=None)[0][3]))
        except Exception: pass
    rows.append({'color':str(color),'n':len(y),'interaction_ols':float(beta[3]),'bootstrap_2_5_97_5':np.quantile(vals,[.025,.975]).tolist(),'sugar_q05_q95':np.quantile(g['residual_sugar'].astype(float),[.05,.95]).tolist()})
print(json.dumps({'diagnostic':'OLS interval-score approximation; row bootstrap assumes independent samples; not causal','results':rows},separators=(',',':')))