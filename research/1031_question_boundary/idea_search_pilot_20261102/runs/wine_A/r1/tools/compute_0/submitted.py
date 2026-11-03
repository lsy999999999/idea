import json, math
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import chi2

df = TABLES['main'].copy()
chem = ['fixed_acidity','volatile_acidity','citric_acid','residual_sugar','chlorides','free_sulfur_dioxide','total_sulfur_dioxide','density','pH','sulphates','alcohol']
cols = chem + ['quality','color']
df = df[cols].dropna().copy()
keep = np.ones(len(df), dtype=bool)
for color in df['color'].unique():
    ix = df['color'].eq(color)
    for v in ['alcohol','residual_sugar']:
        lo, hi = df.loc[ix,v].quantile([.05,.95])
        keep &= ~(ix & ((df[v] < lo) | (df[v] > hi))).to_numpy()
df = df.loc[keep].reset_index(drop=True)
yvals = sorted(df.quality.unique())
y = np.searchsorted(yvals, df.quality.to_numpy())
white = df.color.eq('white').to_numpy(dtype=float)
base = []
names = []
for v in chem:
    mu, sd = df[v].mean(), df[v].std()
    base.append((df[v].to_numpy()-mu)/(sd if sd else 1.0)); names.append(v)
base.append(white); names.append('white')
a = base[names.index('alcohol')]
s = base[names.index('residual_sugar')]
X0 = np.column_stack(base)
X1 = np.column_stack(base + [a*s, a*s*white])

def fit(X):
    n, p = X.shape
    k = len(yvals)-1
    def unpack(t):
        b = t[:p]
        cuts = np.r_[t[p], t[p]+np.cumsum(np.exp(np.clip(t[p+1:p+k],-20,20)))]
        return b,cuts
    def nll(t):
        b,cuts = unpack(t)
        eta = X @ b
        z = np.clip(cuts[None,:]-eta[:,None],-35,35)
        cum = 1/(1+np.exp(-z))
        probs = np.column_stack([cum[:,0], np.diff(cum,axis=1), 1-cum[:,-1]])
        return -np.log(np.maximum(probs[np.arange(n),y],1e-15)).sum()
    start = np.zeros(p+k)
    fr = np.array([(y==j).mean() for j in range(k)])
    q = np.clip(np.cumsum(fr),1e-4,1-1e-4)
    cuts = np.log(q/(1-q))
    start[p] = cuts[0]
    if k>1: start[p+1:p+k] = np.log(np.maximum(np.diff(cuts),1e-3))
    res = minimize(nll,start,method='L-BFGS-B',options={'maxiter':500,'ftol':1e-9})
    b,cuts = unpack(res.x)
    return {'ok':bool(res.success),'nll':float(res.fun),'beta':b.tolist(),'message':str(res.message)}
r0,r1 = fit(X0),fit(X1)
lr=max(0.0,2*(r0['nll']-r1['nll']))
out={'n':len(df),'counts_by_color':df.color.value_counts().to_dict(),'quality_levels':yvals,'central_range_rule':'within-color 5th-95th percentile for alcohol and residual_sugar','base_fit':r0,'interaction_fit':r1,'interaction_terms':['alcohol_x_residual_sugar','alcohol_x_residual_sugar_x_white'],'lr_stat_2df':lr,'lr_p_approx':float(chi2.sf(lr,2)),'white_interaction_sum':float(r1['beta'][-2]+r1['beta'][-1]),'warning':'No lot identifiers; row independence and causal interpretation are unverified.'}
print(json.dumps(out,separators=(',',':')))