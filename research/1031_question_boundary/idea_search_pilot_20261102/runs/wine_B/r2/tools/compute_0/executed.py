import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/idea_search_pilot_20261102/setup/uci186.csv')
TABLES={"main":DF}
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors

rng = np.random.default_rng(20261102)
cols = ['fixed_acidity','volatile_acidity','citric_acid','residual_sugar','chlorides','free_sulfur_dioxide','total_sulfur_dioxide','density','pH','sulphates','alcohol']
out = {}
for color, g in TABLES['main'].groupby('color'):
    X = StandardScaler().fit_transform(g[cols].to_numpy(dtype=float))
    y = g['quality'].to_numpy(dtype=float)
    n = len(g)
    nn = NearestNeighbors(n_neighbors=2).fit(X).kneighbors(X, return_distance=False)[:, 1]
    pairs = sorted(set((min(i, int(j)), max(i, int(j))) for i, j in enumerate(nn)))
    a = np.array([p[0] for p in pairs], dtype=int)
    b = np.array([p[1] for p in pairs], dtype=int)
    observed = float(np.mean(np.abs(y[a] - y[b])))
    pcs = PCA(n_components=2).fit_transform(X)
    strata = np.zeros(n, dtype=int)
    for j in range(2):
        strata = strata * 4 + pd.qcut(pcs[:, j], q=4, labels=False, duplicates='drop').astype(int)
    groups = [np.flatnonzero(strata == s) for s in np.unique(strata)]
    perm = []
    for _ in range(500):
        yp = y.copy()
        for ix in groups:
            yp[ix] = rng.permutation(yp[ix])
        perm.append(float(np.mean(np.abs(yp[a] - yp[b]))))
    perm = np.asarray(perm)
    out[str(color)] = {'n_rows': n, 'n_unique_pairs': len(pairs), 'n_strata': len(groups), 'min_stratum_n': int(min(map(len, groups))), 'observed_mean_abs_quality_difference': observed, 'permutation_mean': float(perm.mean()), 'permutation_interval_95': [float(np.quantile(perm, .025)), float(np.quantile(perm, .975))], 'fraction_permutations_at_least_as_favorable': float(np.mean(perm <= observed))}
print(json.dumps(out, separators=(',', ':')))