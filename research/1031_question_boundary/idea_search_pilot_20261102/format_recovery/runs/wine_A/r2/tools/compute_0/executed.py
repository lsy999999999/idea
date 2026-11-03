import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/idea_search_pilot_20261102/setup/uci186.csv')
TABLES={"main":DF}
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import chi2

df=TABLES['main'].copy()
chem=['fixed_acidity','volatile_acidity','citric_acid','residual_sugar','chlorides','free_sulfur_dioxide','total_sulfur_dioxide','density','pH','sulphates','alcohol']
df=df[chem+['quality','color']].dropna().copy()
keep=np.ones(len(df),dtype=bool)
for c in df.color.unique():
    ix=df.color.eq(c)
    for v in ['alcohol','residual_sugar']:
        lo,hi=df.loc[ix,v].quantile([.05,.95])
        keep &= ~(ix & ((df[v]<lo)|(df[v]>hi))).to_numpy()
df=df.loc[keep].reset_index(drop=True)
levels=sorted(int(v) for v in df.quality.unique())
y=np.searchsorted(levels,df.quality.to_numpy())
w=df.color.eq('white').to_numpy(float)
cols=[]; names=[]
for v in chem:
    z=df[v].to_numpy(float); sd=z.std()
    cols.append((z-z.mean())/(sd if sd else 1.)); names.append(v)
cols.append(w); names.append('white')
a=cols[names.index('alcohol')]; s=cols[names.index('residual_sugar')]
cols += [a*a,s*s]; names += ['alcohol_sq','sugar_sq']
terms=[a*s,a*s*s,a*a*s]
X0=np.column_stack(cols)
X1=np.column_stack(cols+terms+[w*t for t in terms])
def fit(X):
    n,p=X.shape; k=len(levels)-1
    cum=np.array([(y<=j).mean() for j in range(k)])
    cuts=np.log(np.clip(cum,1e-5,1-1e-5)/(1-np.clip(cum,1e-5,1-1e-5)))
    start=np.r_[np.zeros(p),cuts[0],np.log(np.maximum(np.diff(cuts),1e-3))]
    def unpack(t): return t[:p],np.r_[t[p],t[p]+np.cumsum(np.exp(np.clip(t[p+1:],-20,20)))]
    def loss(t):
        b,c=unpack(t); q=1/(1+np.exp(-np.clip(c[None,:]-X@b[:,None],-35,35)))
        pr=np.column_stack([q[:,0],np.diff(q,axis=1),1-q[:,-1]])
        return -np.log(np.maximum(pr[np.arange(n),y],1e-15)).sum()
    r=minimize(loss,start,method='L-BFGS-B',options={'maxiter':700,'ftol':1e-9})
    return {'success':bool(r.success),'message':str(r.message),'nll':float(r.fun),'beta':[float(v) for v in r.x[:p]]}
r0=fit(X0); r1=fit(X1); lr=max(0.,2*(r0['nll']-r1['nll']))
print(json.dumps({'n':int(len(df)),'counts_by_color':{str(k):int(v) for k,v in df.color.value_counts().items()},'quality_levels':levels,'range_rule':'within-color marginal 5th-95th percentiles for alcohol and residual_sugar','base_fit':r0,'expanded_fit':r1,'interaction_terms':['a*s','a*s^2','a^2*s','white*a*s','white*a*s^2','white*a^2*s'],'lr_stat_6df':float(lr),'lr_p_approx':float(chi2.sf(lr,6)),'warning':'Marginal ranges do not guarantee joint support; row independence and causal interpretation are unverified.'},separators=(',',':')))