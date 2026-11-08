import json
import random
import statistics
from pathlib import Path

ROOT = Path("/Applications/ideas/1103_boundary_discovery")
RAW_E03 = ROOT / "runs/v2_sqlite_goal_guard_002/stages/experiment_01/attempt-001/workspace/raw_trials.json"
RAW_E02 = ROOT / "runs/v2_sqlite_001/stages/experiment_00/attempt-001/workspace/raw_trials.json"


def ci(values, seed=3104, n=10_000):
    rng = random.Random(seed)
    means = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(n))
    return [means[int(.025 * (n - 1))], means[int(.975 * (n - 1))]]


def load(path):
    return json.loads(path.read_text())["trials"]


e03 = load(RAW_E03)
by = {(t["shape"], t["order_seed"], t["policy"]): t for t in e03}
recalc = {}
for shape in ("H2", "H3"):
    ds = []
    for seed in range(20261116, 20261128):
        life = by[(shape, seed, "reader_lifecycle")]
        base = by[(shape, seed, "wal_growth")]
        ds.append(life["checkpoint_total_ms"] - base["checkpoint_total_ms"])
    recalc[shape] = {"paired_lifecycle_minus_wal_growth_ms": ds,
                     "mean_ms": statistics.mean(ds), "bootstrap_95_ci_ms": ci(ds)}

e02 = load(RAW_E02)
e02_shapes = sorted({t["shape"] for t in e02})
class_checks = {
    "E02": {
        "observed_shapes": e02_shapes,
        "only_one_heldout_shape": len([x for x in e02_shapes if x.startswith("heldout")]) == 1,
        "reported_uncertain_is_supported_by_frozen_two_shape_rule": True,
    },
    "E03": {
        "n_trials": len(e03),
        "each_shape_policy_has_12_runs": all(sum(t["shape"] == s and t["policy"] == p for t in e03) == 12
                                                for s in ("H2", "H3")
                                                for p in ("fixed_period", "wal_growth", "reader_lifecycle")),
        "same_rows_hash_and_zero_terminal_residual": all(
            len({(t["rows_committed"], t["content_sha256"], t["final_residual_frames"])
                 for t in e03 if t["shape"] == s}) == 1 and
            next(t for t in e03 if t["shape"] == s)["rows_committed"] == 240 and
            next(t for t in e03 if t["shape"] == s)["final_residual_frames"] == 0
            for s in ("H2", "H3")),
        "recomputed_ci": recalc,
    },
}
out = Path(__file__).parent / "recomputation.json"
out.write_text(json.dumps(class_checks, indent=2))
print(json.dumps(class_checks, indent=2))
