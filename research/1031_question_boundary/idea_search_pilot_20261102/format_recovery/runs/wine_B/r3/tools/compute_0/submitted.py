import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

rng = np.random.default_rng(20261102)
cols = ['fixed_acidity','volatile_acidity','citric_acid','residual_sugar','chlorides','free_sulfur_dioxide','total_sulfur_dioxide','density','pH','sulphates','alcohol']
out = {}

def fit_model(X, y, levels, partial):
    # Cumulative-logit likelihood; optimize unconstrained threshold logits,
    # sorting them per row to ensure valid nonnegative category probabilities.
    K, p = len(levels) - 1, X.shape[1]
    q = K * (p + 1) if partial else K + p
    def probs(par, Xb):
        if partial:
            z = par.reshape(K, p + 1)
            eta = z[:, 0][None, :] - Xb @ z[:, 1:].T
        else:
            z = par[:K]
            eta = z[None, :] - (Xb @ par[K:])[:, None]
        c = expit(np.sort(eta, axis=1))
        return np.column_stack([c[:, 0], np.diff(c, axis=1), 1 - c[:, -1]])
    yi = np.searchsorted(levels, y)
    def loss(par):
        pr = probs(par, X)
        return -np.log(np.maximum(pr[np.arange(len(y)), yi], 1e-12)).mean()
    opt = minimize(loss, np.zeros(q), method='L-BFGS-B', options={'maxiter': 250, 'ftol': 1e-8})
    return opt.x, opt.success

for color, g in TABLES['main'].groupby('color'):
    g = g.reset_index(drop=True)
    y = g['quality'].to_numpy(dtype=int)
    levels = np.sort(np.unique(y))
    order = rng.permutation(len(g))
    cut = int(.8 * len(g))
    tr, te = order[:cut], order[cut:]
    mu = g.loc[tr, cols].mean().to_numpy()
    sd = g.loc[tr, cols].std(ddof=0).to_numpy()
    sd[sd == 0] = 1
    X = (g[cols].to_numpy(dtype=float) - mu) / sd
    pars, ok_common = fit_model(X[tr], y[tr], levels, False)
    part, ok_partial = fit_model(X[tr], y[tr], levels, True)
    def test_loss(par, partial):
        K, p = len(levels)-1, X.shape[1]
        if partial:
            z = par.reshape(K, p+1)
            eta = z[:, 0][None, :] - X[te] @ z[:, 1:].T
        else:
            eta = par[None, :K] - (X[te] @ par[K:])[:, None]
        c = expit(np.sort(eta, axis=1))
        pr = np.column_stack([c[:, 0], np.diff(c, axis=1), 1-c[:, -1]])
        yi = np.searchsorted(levels, y[te])
        return -np.log(np.maximum(pr[np.arange(len(te)), yi], 1e-12)).mean()
    out[str(color)] = {'n_train':len(tr),'n_test':len(te),'class_counts':{str(int(v)):int((y==v).sum()) for v in levels},'cumulative_train_counts':{str(int(v)): {'at_or_below':int((y[tr]<=v).sum()),'above':int((y[tr]>v).sum())} for v in levels[:-1]},'common_test_ordinal_log_loss':test_loss(pars,False),'partial_test_ordinal_log_loss':test_loss(part,True),'optimizer_success':{'common':bool(ok_common),'partial':bool(ok_partial)}}
print(json.dumps(out,separators=(',',':')))