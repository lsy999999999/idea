import json
import numpy as np

keys = ["Cement", "Blast Furnace Slag", "Fly Ash", "Water", "Superplasticizer", "Coarse Aggregate", "Fine Aggregate"]
age = "Age"
y = "Concrete compressive strength"
d = DF[keys + [age, y]].copy()
g = d.groupby(keys + [age], as_index=False, dropna=False).agg(strength=(y, "mean"), rows=(y, "size"))
p = g.pivot(index=keys, columns=age, values="strength")
counts = g.pivot(index=keys, columns=age, values="rows")
out = {"unit": "exact ingredient formulation; not batch", "duplicate_formulation_age_cells": int((g["rows"] > 1).sum()), "paired_formulations": 0, "paired_by_group": {"cement_only": 0, "scm_share_gt_0_30": 0}, "overlap": False, "overlap_bounds": {}, "overlap_counts": {"cement_only": 0, "scm_share_gt_0_30": 0}, "summaries": {}, "median_ratio_difference_scm_minus_cement": None, "bootstrap_95pct_interval": None, "note": "No batch or curing identifiers are available; this is a formulation-level descriptive contrast."}
if 7 in p.columns and 28 in p.columns:
    z = p.dropna(subset=[7, 28]).reset_index()
    out["paired_formulations"] = int(len(z))
    binder = z["Cement"] + z["Blast Furnace Slag"] + z["Fly Ash"]
    z["scm_share"] = (z["Blast Furnace Slag"] + z["Fly Ash"]) / binder
    z["water_binder_ratio"] = z["Water"] / binder
    z["early_fraction"] = z[7] / z[28]
    z["strength_gain_mpa"] = z[28] - z[7]
    z["group"] = np.where(z["scm_share"] == 0, "cement_only", np.where(z["scm_share"] > 0.30, "scm_share_gt_0_30", "exclude"))
    a = z[z["group"] == "cement_only"].copy()
    b = z[z["group"] == "scm_share_gt_0_30"].copy()
    out["paired_by_group"] = {"cement_only": int(len(a)), "scm_share_gt_0_30": int(len(b))}
    if len(a) and len(b):
        bounds = {}
        for col in [28, "water_binder_ratio"]:
            lo = max(float(a[col].min()), float(b[col].min()))
            hi = min(float(a[col].max()), float(b[col].max()))
            bounds[str(col)] = [lo, hi]
        out["overlap_bounds"] = bounds
        out["overlap"] = all(v[0] <= v[1] for v in bounds.values())
        if out["overlap"]:
            def in_bounds(frame):
                return frame[28].between(*bounds["28"]) & frame["water_binder_ratio"].between(*bounds["water_binder_ratio"])
            a = a[in_bounds(a)]
            b = b[in_bounds(b)]
            out["overlap_counts"] = {"cement_only": int(len(a)), "scm_share_gt_0_30": int(len(b))}
            if len(a) and len(b):
                def stats(frame):
                    return {"n_formulations": int(len(frame)), "median_early_fraction": float(frame["early_fraction"].median()), "median_strength_gain_mpa": float(frame["strength_gain_mpa"].median())}
                out["summaries"] = {"cement_only": stats(a), "scm_share_gt_0_30": stats(b)}
                delta = float(b["early_fraction"].median() - a["early_fraction"].median())
                out["median_ratio_difference_scm_minus_cement"] = delta
                if len(a) >= 2 and len(b) >= 2:
                    rng = np.random.default_rng(20261102)
                    av = a["early_fraction"].to_numpy()
                    bv = b["early_fraction"].to_numpy()
                    boot = np.empty(5000)
                    for i in range(len(boot)):
                        boot[i] = np.median(rng.choice(bv, len(bv), replace=True)) - np.median(rng.choice(av, len(av), replace=True))
                    q = np.quantile(boot, [0.025, 0.975])
                    out["bootstrap_95pct_interval"] = [float(q[0]), float(q[1])]
print(json.dumps(out, allow_nan=False, separators=(",", ":")))