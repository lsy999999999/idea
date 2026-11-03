import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/idea_search_pilot_20261102/format_recovery/setup/uci468.csv')
TABLES={"main":DF}
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize

x = DF.loc[(DF['ProductRelated'] > 0) & DF['VisitorType'].isin(['New_Visitor', 'Returning_Visitor'])].copy().reset_index(drop=True)
y = x['Revenue'].astype(int).to_numpy()
new = (x['VisitorType'].to_numpy() == 'New_Visitor').astype(float)
raw = np.log1p((x['ProductRelated_Duration'] / x['ProductRelated']).to_numpy(dtype=float))
count = np.log1p(x['ProductRelated'].to_numpy(dtype=float))
months = pd.get_dummies(x['Month'], drop_first=True, dtype=float).to_numpy()

def analyze(v):
    z = (v - v.mean()) / (v.std() or 1.0)
    X = np.column_stack([np.ones(len(z)), z, z*z, new, z*new, z*z*new, count, months])
    def objective(b):
        eta = np.clip(X @ b, -30, 30)
        return np.logaddexp(0, eta).sum() - y @ eta + 1e-8*(b @ b)
    res = minimize(objective, np.zeros(X.shape[1]), method='L-BFGS-B')
    b = res.x
    p = 1/(1+np.exp(-np.clip(X @ b, -30, 30)))
    H = X.T @ (X * (p*(1-p))[:,None]) + np.eye(X.shape[1])*1e-8
    cov = np.linalg.pinv(H)
    ids = [2,5]
    terms = {str(i): {'estimate':float(b[i]),'ci95':[float(b[i]-1.96*np.sqrt(max(cov[i,i],0))),float(b[i]+1.96*np.sqrt(max(cov[i,i],0)))]} for i in ids}
    q = np.quantile(z,[.05,.95])
    slopes = {'Returning_Visitor':[float(b[1]+2*b[2]*t) for t in q], 'New_Visitor':[float(b[1]+b[4]+2*(b[2]+b[5])*t) for t in q]}
    return {'success':bool(res.success),'curvature_terms':terms,'slope_at_proxy_p05_p95':slopes}

counts = x.groupby(['VisitorType','Revenue']).size().unstack(fill_value=0).to_dict(orient='index')
cap = np.minimum(raw, np.quantile(raw,.99))
print(json.dumps({'n':len(x),'counts':counts,'ordinary':analyze(raw),'cap99':analyze(cap)},separators=(',',':')))