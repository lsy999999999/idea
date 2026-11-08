from __future__ import annotations

import json
import random
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path

OUT = Path(__file__).parent
SEEDS = list(range(20261104, 20261116))
POLICIES = ["fixed_period", "wal_growth", "reader_lifecycle"]
TRACE_SHAPES = {
    "development": {
        "readers": {2: [("A", "begin")], 6: [("A", "release")], 13: [("B", "begin")], 16: [("B", "release")]},
        "bursts": [(1, 6), (10, 16), (21, 24)],
    },
    "heldout_H1": {
        "readers": {5: [("A", "begin")], 18: [("A", "release")], 20: [("B", "begin")], 22: [("B", "release")]},
        "bursts": [(1, 5), (8, 18), (21, 24)],
    },
}


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int((len(ordered) - 1) * p)))]


def bootstrap_ci(values, seed=9173, n=10000):
    rng = random.Random(seed)
    means = [statistics.mean(rng.choices(values, k=len(values))) for _ in range(n)]
    means.sort()
    return [means[int(.025 * (n - 1))], means[int(.975 * (n - 1))]]


def run_trial(shape_name, shape, seed, policy):
    with tempfile.TemporaryDirectory(prefix="e02-") as td:
        db = Path(td) / "trial.sqlite"
        writer = sqlite3.connect(db, timeout=.001)
        writer.execute("PRAGMA page_size=4096")
        mode = writer.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        writer.execute("PRAGMA synchronous=NORMAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
        writer.commit()
        readers = {n: sqlite3.connect(db, timeout=.001) for n in ("A", "B")}
        active = set()
        reader_started = {}
        reader_delay_ms = []
        commits_ms = []
        commit_completed_ms = []
        checkpoint_calls = []
        commits_since_attempt = 0
        wal_growth_since_attempt = 0
        last_wal_bytes = 0
        last_tuple = (0, 0, 0)
        t0 = time.perf_counter_ns()
        previous_commit = 0

        def wall_ms():
            return (time.perf_counter_ns() - t0) / 1e6

        def wal_bytes():
            p = Path(str(db) + "-wal")
            return p.stat().st_size if p.exists() else 0

        def checkpoint(trigger, cleanup=False):
            nonlocal commits_since_attempt, wal_growth_since_attempt, last_tuple
            before_bytes = wal_bytes()
            start = time.perf_counter_ns()
            result = writer.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
            duration_ms = (time.perf_counter_ns() - start) / 1e6
            after_bytes = wal_bytes()
            old_log, old_ckpt = last_tuple[1], last_tuple[2]
            advanced = max(0, result[2] - old_ckpt) if result[1] >= old_log else result[2]
            checkpoint_calls.append({
                "trigger": trigger, "cleanup": cleanup, "t_ms": wall_ms(),
                "busy": result[0], "log_frames": result[1], "checkpointed_frames": result[2],
                "frames_advanced_since_prior_call": advanced, "duration_ms": duration_ms,
                "wal_bytes_before": before_bytes, "wal_bytes_after": after_bytes,
                "residual_frames": max(0, result[1] - result[2]),
            })
            last_tuple = tuple(result)
            commits_since_attempt = 0
            wal_growth_since_attempt = 0
            return result

        def events_at(i):
            for name, action in shape["readers"].get(i, []):
                if action == "begin":
                    readers[name].execute("BEGIN")
                    readers[name].execute("SELECT count(*) FROM sample").fetchone()
                    reader_started[name] = wall_ms()
                    active.add(name)
                else:
                    readers[name].rollback()
                    readers[name].close()
                    active.discard(name)
                    reader_delay_ms.append(wall_ms() - reader_started[name])
                    readers[name] = sqlite3.connect(db, timeout=.001)
                    if policy == "reader_lifecycle" and commits_since_attempt:
                        checkpoint("last_reader_release")

        burst_breaks = {a for a, _ in shape["bursts"][1:]}
        burst_inner = {i for a, b in shape["bursts"] for i in range(a + 1, b + 1)}
        for i in range(1, 25):
            if i in burst_breaks:
                time.sleep(.002)
            elif i in burst_inner:
                time.sleep(.00025)
            start = time.perf_counter_ns()
            writer.executemany("INSERT INTO sample(value) VALUES (?)", [(f"{i}:{j}",) for j in range(10)])
            writer.commit()
            commits_ms.append((time.perf_counter_ns() - start) / 1e6)
            commit_completed_ms.append(wall_ms())
            current_bytes = wal_bytes()
            wal_growth_since_attempt += max(0, current_bytes - last_wal_bytes)
            last_wal_bytes = current_bytes
            commits_since_attempt += 1
            events_at(i)
            if policy == "fixed_period" and i % 6 == 0:
                checkpoint("every_6_commits")
            elif policy == "wal_growth" and wal_growth_since_attempt >= 32768:
                checkpoint("32768_bytes_growth")
        for name in list(active):
            readers[name].rollback()
            readers[name].close()
            reader_delay_ms.append(wall_ms() - reader_started[name])
        if last_tuple[1] > last_tuple[2]:
            checkpoint("final_residual_cleanup", cleanup=True)
        final = last_tuple
        result = {
            "shape": shape_name, "order_seed": seed, "policy": policy,
            "sqlite_version": sqlite3.sqlite_version, "journal_mode": mode,
            "page_size": writer.execute("PRAGMA page_size").fetchone()[0],
            "rows_committed": writer.execute("SELECT count(*) FROM sample").fetchone()[0],
            "checkpoint_calls": checkpoint_calls,
            "checkpoint_call_count": len(checkpoint_calls),
            "checkpoint_total_ms": sum(x["duration_ms"] for x in checkpoint_calls),
            "final_busy_log_checkpointed": list(final),
            "final_residual_frames": max(0, final[1] - final[2]),
            "peak_wal_bytes": max([x["wal_bytes_before"] for x in checkpoint_calls] + [last_wal_bytes]),
            "writer_commit_p95_ms": percentile(commits_ms, .95),
            "writer_commit_p99_ms": percentile(commits_ms, .99),
            "reader_completion_delay_ms": reader_delay_ms,
            "reader_completion_delay_max_ms": max(reader_delay_ms, default=0),
            "commit_completion_times_ms": commit_completed_ms,
        }
        writer.close()
        return result


def main():
    trials = []
    order_log = []
    for shape_name, shape in TRACE_SHAPES.items():
        for seed in SEEDS:
            order = POLICIES.copy()
            random.Random(seed + (0 if shape_name == "development" else 1000)).shuffle(order)
            order_log.append({"shape": shape_name, "seed": seed, "order": order})
            for policy in order:
                trials.append(run_trial(shape_name, shape, seed, policy))
    (OUT / "raw_trials.json").write_text(json.dumps({
        "sqlite_version": sqlite3.sqlite_version, "trials": trials, "orders": order_log,
    }, indent=2))
    summary = {}
    for shape_name in TRACE_SHAPES:
        by_key = {(t["order_seed"], t["policy"]): t for t in trials if t["shape"] == shape_name}
        shape_summary = {}
        for p in POLICIES:
            group = [by_key[(s, p)] for s in SEEDS]
            shape_summary[p] = {
                "checkpoint_total_ms_mean": statistics.mean(t["checkpoint_total_ms"] for t in group),
                "calls_mean": statistics.mean(t["checkpoint_call_count"] for t in group),
                "final_checkpointed_frames_min": min(t["final_busy_log_checkpointed"][2] for t in group),
                "final_log_frames_min": min(t["final_busy_log_checkpointed"][1] for t in group),
                "residual_frames_max": max(t["final_residual_frames"] for t in group),
                "peak_wal_bytes_max": max(t["peak_wal_bytes"] for t in group),
                "writer_p95_ms_mean": statistics.mean(t["writer_commit_p95_ms"] for t in group),
                "writer_p99_ms_mean": statistics.mean(t["writer_commit_p99_ms"] for t in group),
                "reader_delay_max_ms_mean": statistics.mean(t["reader_completion_delay_max_ms"] for t in group),
            }
        comparisons = {}
        life = [by_key[(s, "reader_lifecycle")] for s in SEEDS]
        for base in ("fixed_period", "wal_growth"):
            b = [by_key[(s, base)] for s in SEEDS]
            checkpoint_d = [x["checkpoint_total_ms"] - y["checkpoint_total_ms"] for x, y in zip(life, b)]
            writer_d = [x["writer_commit_p95_ms"] - y["writer_commit_p95_ms"] for x, y in zip(life, b)]
            reader_d = [x["reader_completion_delay_max_ms"] - y["reader_completion_delay_max_ms"] for x, y in zip(life, b)]
            comparisons[base] = {
                "lifecycle_minus_baseline_checkpoint_ms_mean": statistics.mean(checkpoint_d),
                "checkpoint_ms_95pct_bootstrap_ci": bootstrap_ci(checkpoint_d),
                "lifecycle_minus_baseline_writer_p95_ms_mean": statistics.mean(writer_d),
                "writer_p95_95pct_bootstrap_ci": bootstrap_ci(writer_d, seed=9174),
                "lifecycle_minus_baseline_reader_delay_max_ms_mean": statistics.mean(reader_d),
                "reader_delay_95pct_bootstrap_ci": bootstrap_ci(reader_d, seed=9175),
                "completion_frames_lifecycle_ge_baseline_all_pairs": all(
                    x["final_busy_log_checkpointed"][2] >= y["final_busy_log_checkpointed"][2]
                    for x, y in zip(life, b)),
            }
        shape_summary["paired_comparisons"] = comparisons
        summary[shape_name] = shape_summary
    (OUT / "classification.json").write_text(json.dumps({
        "predeclared_rule": "specific classes require two held-out shapes; the frozen intervention contains one, so neither lifecycle_gain nor baseline_sufficient can be established; uncertain_or_tradeoff applies under the plan's insufficient-data condition",
        "classification": "uncertain_or_tradeoff",
        "shape_summaries": summary,
    }, indent=2))
    print(json.dumps({"trials": len(trials), "classification": "uncertain_or_tradeoff", "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
