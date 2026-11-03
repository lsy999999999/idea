import json
import numpy as np
from scipy.optimize import minimize

chem=['fixed_acidity','volatile_acidity','citric_acid','residual_sugar','chlorides','free_sulfur_dioxide','total_sulfur_dioxide','density','pH','sulphates','alcohol']
out=[]
def fit(X,y):
    def loss(b):
        z=np.clip(X@b,-30,30)
        return np.logaddexp(0,z).sum()-y@z
    r=minimize(loss,np.zeros(X.shape[1]),method='L-BFGS-B',options={'maxiter':300,'ftol':1e-10})
    return float(r.x[1]),bool(r.success)
for color,g0 in DF.groupby('color'):
    g=g0.reset_index(drop=True); raw=g[chem].astype(float).to_numpy(); mu=raw.mean(0); sd=raw.std(0); sd[sd==0]=1
    z=(raw-mu)/sd; X=np.column_stack([np.ones(len(g)),z]); q=g['quality'].astype(int).to_numpy()
    yl=(q<=5).astype(float); yh=(q>=7).astype(float)
    bl,okl=fit(X,yl); bh,okh=fit(X,yh); rng=np.random.default_rng(20261102); vals=[]
    for _ in range(120):
        ix=rng.integers(0,len(q),len(q))
        if len(np.unique(yl[ix]))<2 or len(np.unique(yh[ix]))<2: continue
        try:
            a,sa=fit(X[ix],yl[ix]); b,sb=fit(X[ix],yh[ix])
            if sa and sb: vals.append(abs(a)-abs(b))
        except Exception: pass
    out.append({'color':str(color),'n':len(q),'low_event_n':int(yl.sum()),'high_event_n':int(yh.sum()),'low_coef':bl,'high_coef':bh,'abs_strength_difference_low_minus_high':abs(bl)-abs(bh),'paired_bootstrap_2_5_97_5':np.quantile(vals,[.025,.975]).tolist() if vals else None,'bootstrap_successes':len(vals),'fits_converged':[okl,okh]})
print(json.dumps({'scale':'standardized volatile_acidity log-odds; difference is absolute low-event coefficient minus absolute high-event coefficient','caveat':'paired row bootstrap assumes independent samples; exploratory and noncausal','results':out},separators=(',',':'))