import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/idea_search_pilot_20261102/format_recovery/setup/uci468.csv')
TABLES={"main":DF}
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize

x = DF.loc[DF['Informational'] > 0].copy().reset_index(drop=True)
y = x['Revenue'].astype(int).to_numpy()
sd = (x['SpecialDay'].to_numpy(dtype=float) > 0).astype(float)
d = np.log1p(x['Informational_Duration'].to_numpy(dtype=float))
count = np.log1p(x['Informational'].to_numpy(dtype=float))

def fit_frame(frame):
    yy = frame['Revenue'].astype(int).to_numpy()
    ss = (frame['SpecialDay'].to_numpy(dtype=float) > 0).astype(float)
    dd = np.log1p(frame['Informational_Duration'].to_numpy(dtype=float))
    zz = (dd - dd.mean()) / (dd.std() or 1.0)
    cc = np.log1p(frame['Informational'].to_numpy(dtype=float))
    vt = pd.get_dummies(frame['VisitorType'], drop_first=True, dtype=float).to_numpy()
    mo = pd.get_dummies(frame['Month'], drop_first=True, dtype=float).to_numpy()
    X = np.column_stack([np.ones(len(frame)), zz, ss, zz*ss, cc, vt, mo])
    def objective(b):
        eta = np.clip(X @ b, -30, 30)
        return np.logaddexp(0, eta).sum() - yy @ eta + 1e-8*(b @ b)
    res = minimize(objective, np.zeros(X.shape[1]), method='L-BFGS-B')
    b = res.x
    p = 1/(1+np.exp(-np.clip(X @ b, -30, 30)))
    H = X.T @ (X * (p*(1-p))[:,None]) + np.eye(X.shape[1])*1e-8
    cov = np.linalg.pinv(H)
    j = 3
    se = float(np.sqrt(max(cov[j,j], 0)))
    return {'success':bool(res.success),'interaction':float(b[j]),'ci95':[float(b[j]-1.96*se),float(b[j]+1.96*se)],'n':len(frame),'counts':frame.assign(_sd=ss).groupby(['_sd','Revenue']).size().unstack(fill_value=0).to_dict(orient='index')}

base = fit_frame(x)
nonother = fit_frame(x.loc[x['VisitorType'] != 'Other'].reset_index(drop=True))
print(json.dumps({'all':base,'exclude_other':nonother},separators=(',',':')))