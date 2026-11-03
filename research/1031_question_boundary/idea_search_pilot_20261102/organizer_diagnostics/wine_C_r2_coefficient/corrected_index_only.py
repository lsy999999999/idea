import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/idea_search_pilot_20261102/setup/uci186.csv')
TABLES={"main":DF}
import json
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

chem=['fixed_acidity','volatile_acidity','citric_acid','residual_sugar','chlorides','free_sulfur_dioxide','total_sulfur_dioxide','density','pH','sulphates','alcohol']
results=[]
def fit_ord(X,y,k):
    n,p=X.shape
    counts=np.bincount(y,minlength=k).astype(float)
    cum=np.cumsum(counts)[:-1]/len(y)
    init_thr=np.log(np.clip(cum,1e-5,1-1e-5)/(1-np.clip(cum,1e-5,1-1e-5)))
    init=np.r_[np.zeros(p),init_thr[0],np.log(np.maximum(np.diff(init_thr),0.05))]
    def unpack(q):
        z=q[p:]
        th=np.r_[z[0],z[0]+np.cumsum(np.exp(np.clip(z[1:],-8,8)))]
        return q[:p],th
    def loss(q):
        b,th=unpack(q); c=expit(th[None,:]-X@b[:,None])
        probs=np.column_stack([c[:,0],np.diff(c,axis=1),1-c[:,-1]])
        return -np.log(np.clip(probs[np.arange(n),y],1e-12,1)).sum()
    r=minimize(loss,init,method='L-BFGS-B',options={'maxiter':250,'ftol':1e-8})
    return r.x[2],bool(r.success)
for color,g0 in DF.groupby('color'):
    g=g0.reset_index(drop=True); raw=g[chem].astype(float).to_numpy()
    mu=raw.mean(axis=0); sd=raw.std(axis=0); sd[sd==0]=1
    z=(raw-mu)/sd; ia=chem.index('volatile_acidity'); ic=chem.index('citric_acid')
    interaction=z[:,ia]*z[:,ic]
    cols=[z[:,ia],z[:,ic],interaction]+[z[:,j] for j in range(len(chem)) if j not in (ia,ic)]
    X=np.column_stack(cols); cats=sorted(g['quality'].astype(int).unique()); mp={v:i for i,v in enumerate(cats)}
    y=g['quality'].astype(int).map(mp).to_numpy(); k=len(cats)
    est,ok=fit_ord(X,y,k); rng=np.random.default_rng(20261102); boot=[]
    for _ in range(80):
        ix=rng.integers(0,len(y),len(y))
        try:
            b,s=fit_ord(X[ix],y[ix],k)
            if s and np.isfinite(b): boot.append(float(b))
        except Exception: pass
    results.append({'color':str(color),'n':len(y),'interaction_log_odds':float(est),'fit_success':ok,'bootstrap_successes':len(boot),'bootstrap_2_5_97_5':np.quantile(boot,[.025,.975]).tolist() if boot else None,'volatile_acidity_q05_q95':np.quantile(raw[:,ia],[.05,.95]).tolist(),'citric_acid_q05_q95':np.quantile(raw[:,ic],[.05,.95]).tolist()})
print(json.dumps({'model':'proportional odds; standardized predictors; row bootstrap assumes independent samples; not causal','results':results},separators=(',',':')))