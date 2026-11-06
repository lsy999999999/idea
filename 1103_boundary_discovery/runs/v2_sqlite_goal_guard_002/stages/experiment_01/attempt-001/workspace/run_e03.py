from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path

OUT = Path(__file__).parent
SEEDS = list(range(20261116, 20261128))
POLICIES = ["fixed_period", "wal_growth", "reader_lifecycle"]
TRACES = {
    "H2": {
        "readers": {2: [("A", "begin")], 6: [("A", "release")], 15: [("B", "begin")], 16: [("B", "release")]},
        "bursts": [(1, 6), (15, 24)],
    },
    "H3": {
        "readers": {5: [("A", "begin")], 10: [("A", "release")], 18: [("B", "begin")], 24: [("B", "release")]},
        "bursts": [(1, 8), (11, 16), (21, 24)],
    },
}


def percentile(values, p):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int((len(ordered) - 1) * p)))]


def bootstrap_ci(values, seed=3104, n=10000):
    rng = random.Random(seed)
    means = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(n))
    return [means[int(.025 * (n - 1))], means[int(.975 * (n - 1))]]


def run_trial(shape_name, shape, seed, policy):
    with tempfile.TemporaryDirectory(prefix="e03-") as td:
        db = Path(td) / "trial.sqlite"
        writer = sqlite3.connect(db, timeout=.001)
        writer.execute("PRAGMA page_size=4096")
        mode = writer.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        writer.execute("PRAGMA synchronous=NORMAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
        writer.commit()
        readers = {name: sqlite3.connect(db, timeout=.001) for name in ("A", "B")}
        active, started, reader_delays, commit_ms, calls = set(), {}, [], [], []
        commits_since = 0
        growth_since = 0
        last_wal_bytes = 0
        last_tuple = (0, 0, 0)
        t0 = time.perf_counter_ns()

        def elapsed_ms():
            return (time.perf_counter_ns() - t0) / 1e6

        def wal_bytes():
            p = Path(str(db) + "-wal")
            return p.stat().st_size if p.exists() else 0

        def checkpoint(trigger, cleanup=False):
            nonlocal commits_since, growth_since, last_tuple
            before = wal_bytes()
            tic = time.perf_counter_ns()
            result = writer.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
            duration = (time.perf_counter_ns() - tic) / 1e6
            after = wal_bytes()
            calls.append({
                "trigger": trigger, "cleanup": cleanup, "t_ms": elapsed_ms(),
                "busy": result[0], "log_frames": result[1], "checkpointed_frames": result[2],
                "duration_ms": duration, "wal_bytes_before": before, "wal_bytes_after": after,
                "residual_frames": max(0, result[1] - result[2]),
            })
            last_tuple = tuple(result)
            commits_since = growth_since = 0
            return result

        def events_at(i):
            for name, action in shape["readers"].get(i, []):
                if action == "begin":
                    readers[name].execute("BEGIN")
                    readers[name].execute("SELECT count(*) FROM sample").fetchone()
                    started[name] = elapsed_ms()
                    active.add(name)
                else:
                    readers[name].rollback()
                    readers[name].close()
                    active.discard(name)
                    reader_delays.append(elapsed_ms() - started[name])
                    readers[name] = sqlite3.connect(db, timeout=.001)
                    if policy == "reader_lifecycle" and commits_since:
                        checkpoint("last_reader_release")

        burst_breaks = {a for a, _ in shape["bursts"][1:]}
        burst_commits = {i for a, b in shape["bursts"] for i in range(a, b + 1)}
        for i in range(1, 25):
            if i in burst_breaks:
                time.sleep(.002)
            elif i in burst_commits:
                time.sleep(.00025)
            tic = time.perf_counter_ns()
            writer.executemany("INSERT INTO sample(value) VALUES (?)", [(f"{i}:{j}",) for j in range(10)])
            writer.commit()
            commit_ms.append((time.perf_counter_ns() - tic) / 1e6)
            current_bytes = wal_bytes()
            growth_since += max(0, current_bytes - last_wal_bytes)
            last_wal_bytes = current_bytes
            commits_since += 1
            events_at(i)
            if policy == "fixed_period" and i % 6 == 0:
                checkpoint("every_6_commits")
            elif policy == "wal_growth" and growth_since >= 32768:
                checkpoint("32768_bytes_growth")

        for name in list(active):
            readers[name].rollback()
            readers[name].close()
            reader_delays.append(elapsed_ms() - started[name])
        if last_tuple[1] > last_tuple[2]:
            checkpoint("final_residual_cleanup", cleanup=True)
        rows = writer.execute("SELECT id,value FROM sample ORDER BY id").fetchall()
        digest = hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
        result = {
            "shape": shape_name, "order_seed": seed, "policy": policy,
            "sqlite_version": sqlite3.sqlite_version, "journal_mode": mode,
            "page_size": writer.execute("PRAGMA page_size").fetchone()[0],
            "rows_committed": len(rows), "content_sha256": digest,
            "checkpoint_calls": calls, "checkpoint_call_count": len(calls),
            "checkpoint_total_ms": sum(c["duration_ms"] for c in calls),
            "final_busy_log_checkpointed": list(last_tuple),
            "final_residual_frames": max(0, last_tuple[1] - last_tuple[2]),
            "peak_wal_bytes": max([c["wal_bytes_before"] for c in calls] + [last_wal_bytes]),
            "writer_commit_p95_ms": percentile(commit_ms, .95),
            "writer_commit_p99_ms": percentile(commit_ms, .99),
            "reader_completion_delay_ms": reader_delays,
            "reader_completion_delay_max_ms": max(reader_delays, default=0),
        }
        writer.close()
        return result


def main():
    trials, orders = [], []
    for shape_name, shape in TRACES.items():
        for seed in SEEDS:
            order = POLICIES.copy()
            random.Random(seed + (0 if shape_name == "H2" else 1000)).shuffle(order)
            orders.append({"shape": shape_name, "seed": seed, "order": order})
            for policy in order:
                trials.append(run_trial(shape_name, shape, seed, policy))
                (OUT / "raw_trials.json").write_text(json.dumps({"trials": trials, "orders": orders, "trace_specs": TRACES}, indent=2))
    analyses, control_ok = {}, True
    for shape_name in TRACES:
        by_key = {(t["order_seed"], t["policy"]): t for t in trials if t["shape"] == shape_name}
        shape_control = all(
            by_key[(s, p)]["rows_committed"] == 240 and by_key[(s, p)]["final_residual_frames"] == 0
            and by_key[(s, p)]["journal_mode"].lower() == "wal" and by_key[(s, p)]["page_size"] == 4096
            for s in SEEDS for p in POLICIES
        ) and len({by_key[(s, p)]["content_sha256"] for s in SEEDS for p in POLICIES}) == 1
        control_ok &= shape_control
        comparisons, summaries = {}, {}
        for base in ("fixed_period", "wal_growth"):
            life = [by_key[(s, "reader_lifecycle")] for s in SEEDS]
            other = [by_key[(s, base)] for s in SEEDS]
            diffs = {
                "checkpoint_ms": [x["checkpoint_total_ms"] - y["checkpoint_total_ms"] for x, y in zip(life, other)],
                "writer_p95_ms": [x["writer_commit_p95_ms"] - y["writer_commit_p95_ms"] for x, y in zip(life, other)],
                "writer_p99_ms": [x["writer_commit_p99_ms"] - y["writer_commit_p99_ms"] for x, y in zip(life, other)],
                "reader_delay_max_ms": [x["reader_completion_delay_max_ms"] - y["reader_completion_delay_max_ms"] for x, y in zip(life, other)],
            }
            comparisons[base] = {k: {"mean": statistics.mean(v), "bootstrap_95_ci": bootstrap_ci(v, 3104)} for k, v in diffs.items()}
            comparisons[base]["checkpoint_calls_mean"] = statistics.mean(t["checkpoint_call_count"] for t in life)
        for p in POLICIES:
            group = [by_key[(s, p)] for s in SEEDS]
            summaries[p] = {
                "checkpoint_total_ms_mean": statistics.mean(t["checkpoint_total_ms"] for t in group),
                "checkpoint_calls_mean": statistics.mean(t["checkpoint_call_count"] for t in group),
                "peak_wal_bytes_max": max(t["peak_wal_bytes"] for t in group),
                "final_tuple_values": sorted({tuple(t["final_busy_log_checkpointed"]) for t in group}),
                "residual_frames_max": max(t["final_residual_frames"] for t in group),
            }
        analyses[shape_name] = {"control_ok": shape_control, "policies": summaries, "paired": comparisons}
    latencies_ok = all(
        analyses[h]["paired"][b][m]["bootstrap_95_ci"][1] <= 0
        for h in TRACES for b in ("fixed_period", "wal_growth")
        for m in ("writer_p95_ms", "writer_p99_ms", "reader_delay_max_ms")
    )
    gain = control_ok and latencies_ok and all(
        analyses[h]["paired"][b]["checkpoint_ms"]["bootstrap_95_ci"][1] < 0
        for h in TRACES for b in ("fixed_period", "wal_growth")
    )
    sufficient = control_ok and latencies_ok and all(
        any(-analyses[h]["paired"][b]["checkpoint_ms"]["bootstrap_95_ci"][0] <= 0 for b in ("fixed_period", "wal_growth"))
        for h in TRACES
    )
    classification = "lifecycle_gain" if gain else "baseline_sufficient" if sufficient else "uncertain_or_tradeoff"
    (OUT / "classification.json").write_text(json.dumps({
        "predeclared_rule": "E03 frozen plan: paired 95% percentile bootstrap, 10000 resamples, seed 3104; lifecycle_gain requires both H2/H3 and both baselines with checkpoint CI upper <0 and all latency CI uppers <=0; baseline_sufficient requires controls, latency matching, and at least one baseline per shape with baseline-minus-lifecycle checkpoint CI upper <=0; otherwise uncertain_or_tradeoff.",
        "classification": classification, "control_ok": control_ok, "latencies_ok": latencies_ok,
        "n_trials": len(trials), "shapes": analyses,
    }, indent=2))
    print(json.dumps({"n_trials": len(trials), "classification": classification, "control_ok": control_ok, "latencies_ok": latencies_ok, "shapes": analyses}, indent=2))


if __name__ == "__main__":
    main()
