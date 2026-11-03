import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize

df=TABLES['main'].copy()
chem=['fixed_acidity','volatile_acidity','citric_acid','residual_sugar','chlorides','free_sulfur_dioxide','total_sulfur_dioxide','density','pH','sulphates','alcohol']
df=df[chem+['quality','color']].dropna().copy()
levels=sorted(int(v) for v in df.quality.unique())
cols=[]; names=[]
for v in chem:
    z=df[v].to_numpy(float); sd=z.std()
    cols.append((z-z.mean())/(sd if sd else 1.)); names.append(v)
cols.append(df.color.eq('white').to_numpy(float)); names.append('white')
X=np.column_stack([np.ones(len(df))]+cols)
va_idx=names.index('volatile_acidity')+1
results=[]
for j in levels[:-1]:
    y=(df.quality.to_numpy()>j).astype(float)
    n1=int(y.sum()); n0=int(len(y)-n1)
    def loss(b):
        z=np.clip(X@b,-35,35)
        return float(np.logaddexp(0,z).sum()-y@z)
    def grad(b):
        z=np.clip(X@b,-35,35)
        p=1/(1+np.exp(-z))
        return X.T@(p-y)
    r=minimize(loss,np.zeros(X.shape[1]),jac=grad,method='BFGS',options={'maxiter':500,'gtol':1e-7})
    try:
        H=X.T@((lambda p:p*(1-p))(1/(1+np.exp(-np.clip(X@r.x,-35,35))))[:,None]*X)
        cov=np.linalg.pinv(H)
        se=float(np.sqrt(max(cov[va_idx,va_idx],0)))
    except Exception:
        se=None
    results.append({'threshold':int(j),'n_quality_le_threshold':n0,'n_quality_gt_threshold':n1,'converged':bool(r.success),'message':str(r.message),'volatile_acidity_beta':float(r.x[va_idx]),'model_based_se':se})
print(json.dumps({'n':int(len(df)),'quality_levels':levels,'same_rows_all_thresholds':True,'predictors':chem+['white'],'threshold_results':results,'warning':'Descriptive separate cumulative logits; thresholds share rows, model-based standard errors assume independent rows, and neither causality nor lot-level inference is established.'},separators=(',',':')))