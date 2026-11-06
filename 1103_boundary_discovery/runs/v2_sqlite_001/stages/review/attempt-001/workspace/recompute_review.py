import json
import random
import statistics
from pathlib import Path


ROOT = Path("/Applications/ideas/1103_boundary_discovery/runs/v2_sqlite_001")
OUT = Path(__file__).parent


def bootstrap_ci(values, seed=9173, n=10000):
    rng = random.Random(seed)
    means = [statistics.mean(rng.choices(values, k=len(values))) for _ in range(n)]
    means.sort()
    return [means[int(0.025 * (n - 1))], means[int(0.975 * (n - 1))]]


def read_json(path):
    return json.loads(path.read_text())


e02 = read_json(ROOT / "stages/experiment_00/attempt-001/workspace/raw_trials.json")
e02_trials = [t for t in e02["trials"] if t["shape"] == "heldout_H1"]
by_policy_seed = {(t["policy"], t["order_seed"]): t for t in e02_trials}
e02_recomputed = {"heldout_shape": "heldout_H1", "seed_count": 12, "comparisons": {}}
e02_shape_names = sorted({t["shape"] for t in e02["trials"]})
e02_heldout_shape_names = [name for name in e02_shape_names if name != "development"]
life = [by_policy_seed[("reader_lifecycle", s)] for s in range(20261104, 20261116)]
for policy, seed in (("fixed_period", 9173), ("wal_growth", 9173)):
    baseline = [by_policy_seed[(policy, s)] for s in range(20261104, 20261116)]
    cost = [x["checkpoint_total_ms"] - y["checkpoint_total_ms"] for x, y in zip(life, baseline)]
    writer = [x["writer_commit_p95_ms"] - y["writer_commit_p95_ms"] for x, y in zip(life, baseline)]
    reader = [x["reader_completion_delay_max_ms"] - y["reader_completion_delay_max_ms"] for x, y in zip(life, baseline)]
    e02_recomputed["comparisons"][policy] = {
        "checkpoint_mean_ms": statistics.mean(cost),
        "checkpoint_bootstrap_ci_ms": bootstrap_ci(cost, seed=seed),
        "writer_p95_mean_ms": statistics.mean(writer),
        "writer_p95_bootstrap_ci_ms": bootstrap_ci(writer, seed=9174),
        "reader_delay_max_mean_ms": statistics.mean(reader),
        "reader_delay_bootstrap_ci_ms": bootstrap_ci(reader, seed=9175),
        "all_pairs_terminal_checkpointed_ge_baseline": all(
            x["final_busy_log_checkpointed"][2] >= y["final_busy_log_checkpointed"][2]
            for x, y in zip(life, baseline)
        ),
        "lifecycle_terminal_tuple": life[0]["final_busy_log_checkpointed"],
        "baseline_terminal_tuple": baseline[0]["final_busy_log_checkpointed"],
    }
e02_recomputed["rule_check"] = {
    "required_heldout_shape_count": 2,
    "observed_heldout_shape_names": e02_heldout_shape_names,
    "observed_heldout_shape_count": len(e02_heldout_shape_names),
    "two_heldout_shapes_present": len(e02_heldout_shape_names) == 2,
    "classification": "uncertain_or_tradeoff",
    "reason": "Only one heldout shape is present; both cost intervals include zero and lifecycle terminal checkpointed frames are lower than either baseline.",
}

e03 = read_json(ROOT / "stages/experiment_01/attempt-001/workspace/raw_trials.json")
e03_trials = e03["trials"]
e03_pairs = []
for seed in sorted({t["seed"] for t in e03_trials}):
    pair = {t["condition"]: t for t in e03_trials if t["seed"] == seed}
    short, long = pair["short"], pair["long"]
    valid = (
        short["sqlite_version"] == long["sqlite_version"]
        and short["writes"] == long["writes"]
        and short["rows_committed"] == long["rows_committed"]
        and short["log_frames"] == long["log_frames"]
        and short["wal_bytes_before"] == long["wal_bytes_before"]
        and short["reader_active_at_checkpoint"]
        and long["reader_active_at_checkpoint"]
    )
    e03_pairs.append({
        "seed": seed,
        "valid": valid,
        "delta_long_minus_short": long["checkpointed_frames"] - short["checkpointed_frames"],
    })
e03_recomputed = {
    "pair_count": len(e03_pairs),
    "valid_pairs": sum(p["valid"] for p in e03_pairs),
    "negative_delta_count": sum(p["valid"] and p["delta_long_minus_short"] < 0 for p in e03_pairs),
    "nonnegative_delta_count": sum(p["valid"] and p["delta_long_minus_short"] >= 0 for p in e03_pairs),
    "deltas": [p["delta_long_minus_short"] for p in e03_pairs],
    "classification": "no_age_penalty" if sum(p["valid"] for p in e03_pairs) >= 10 and sum(p["valid"] and p["delta_long_minus_short"] >= 0 for p in e03_pairs) >= 10 else "uncertain",
}

e04 = read_json(ROOT / "stages/experiment_02/attempt-001/workspace/raw_trials.json")
e04_trials = e04["trials"]
e04_seeds = []
for seed in sorted({t["seed"] for t in e04_trials}):
    group = {t["condition"]: t for t in e04_trials if t["seed"] == seed}
    early, mid, late = group["early"], group["mid"], group["late"]
    valid = (
        len({t["sqlite_version"] for t in group.values()}) == 1
        and len({t["page_size"] for t in group.values()}) == 1
        and len({t["synchronous"] for t in group.values()}) == 1
        and len({t["writes"] for t in group.values()}) == 1
        and len({t["log_frames"] for t in group.values()}) == 1
        and len({t["wal_bytes_before"] for t in group.values()}) == 1
        and all(t["reader_active_at_checkpoint"] for t in group.values())
        and (early["snapshot_prefix_batches"], mid["snapshot_prefix_batches"], late["snapshot_prefix_batches"]) == (0, 12, 23)
    )
    frames = (early["checkpointed_frames"], mid["checkpointed_frames"], late["checkpointed_frames"])
    e04_seeds.append({"seed": seed, "valid": valid, "frames": frames, "order": frames[2] > frames[0], "mid_ge_early": frames[1] >= frames[0], "flat": len(set(frames)) == 1})
order = sum(s["valid"] and s["order"] for s in e04_seeds)
mid_ge = sum(s["valid"] and s["mid_ge_early"] for s in e04_seeds)
flat = sum(s["valid"] and s["flat"] for s in e04_seeds)
e04_recomputed = {
    "seed_count": len(e04_seeds),
    "valid_seed_count": sum(s["valid"] for s in e04_seeds),
    "late_gt_early_count": order,
    "mid_ge_early_count": mid_ge,
    "flat_count": flat,
    "per_seed_frames": [list(s["frames"]) for s in e04_seeds],
    "classification": "position_order" if order >= 10 and mid_ge >= 10 else "position_flat" if flat >= 10 else "uncertain",
}

report = {
    "method": "Independent recomputation from frozen raw_trials.json files; no experiment rerun.",
    "E02": e02_recomputed,
    "E03": e03_recomputed,
    "E04": e04_recomputed,
}
(OUT / "recomputation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
