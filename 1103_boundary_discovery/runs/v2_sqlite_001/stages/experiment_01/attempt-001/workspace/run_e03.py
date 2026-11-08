from __future__ import annotations

import json
import random
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path


OUT = Path(__file__).parent
SEEDS = list(range(20261116, 20261128))
CONDITIONS = ["short", "long"]
AGE_MS = {"short": 1, "long": 100}
WRITES = 24
ROWS_PER_WRITE = 10
SQL = "INSERT INTO sample(value) VALUES (?)"


def run_trial(seed: int, condition: str, position: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="e03-") as td:
        db = Path(td) / "trial.sqlite"
        writer = sqlite3.connect(db, timeout=5)
        writer.execute("PRAGMA page_size=4096")
        journal_mode = writer.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        writer.execute("PRAGMA synchronous=NORMAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
        writer.commit()

        reader = sqlite3.connect(db, timeout=5)
        reader.execute("BEGIN")
        snapshot_count = reader.execute("SELECT count(*) FROM sample").fetchone()[0]
        snapshot_ready_ns = time.perf_counter_ns()
        time.sleep(AGE_MS[condition] / 1000)
        age_before_writes_ms = (time.perf_counter_ns() - snapshot_ready_ns) / 1e6

        commit_durations_ms = []
        for batch in range(WRITES):
            values = [(f"{batch}:{row}",) for row in range(ROWS_PER_WRITE)]
            start = time.perf_counter_ns()
            writer.executemany(SQL, values)
            writer.commit()
            commit_durations_ms.append((time.perf_counter_ns() - start) / 1e6)

        wal_path = Path(f"{db}-wal")
        wal_bytes_before = wal_path.stat().st_size if wal_path.exists() else 0
        checkpoint_start_ns = time.perf_counter_ns()
        checkpoint = list(writer.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone())
        checkpoint_ms = (time.perf_counter_ns() - checkpoint_start_ns) / 1e6
        wal_bytes_after = wal_path.stat().st_size if wal_path.exists() else 0

        result = {
            "seed": seed,
            "condition": condition,
            "order_position": position,
            "sqlite_version": sqlite3.sqlite_version,
            "journal_mode": journal_mode,
            "page_size": writer.execute("PRAGMA page_size").fetchone()[0],
            "synchronous": writer.execute("PRAGMA synchronous").fetchone()[0],
            "wal_autocheckpoint": writer.execute("PRAGMA wal_autocheckpoint").fetchone()[0],
            "reader_snapshot_count": snapshot_count,
            "reader_active_at_checkpoint": True,
            "requested_age_ms": AGE_MS[condition],
            "measured_age_before_writes_ms": age_before_writes_ms,
            "writes": WRITES,
            "rows_per_write": ROWS_PER_WRITE,
            "rows_committed": WRITES * ROWS_PER_WRITE,
            "commit_durations_ms": commit_durations_ms,
            "busy": checkpoint[0],
            "log_frames": checkpoint[1],
            "checkpointed_frames": checkpoint[2],
            "wal_bytes_before": wal_bytes_before,
            "wal_bytes_after": wal_bytes_after,
            "checkpoint_duration_ms": checkpoint_ms,
        }
        reader.rollback()
        reader.close()
        writer.close()
        return result


def main() -> None:
    trials = []
    orders = []
    for seed in SEEDS:
        order = CONDITIONS.copy()
        random.Random(seed).shuffle(order)
        orders.append({"seed": seed, "order": order})
        for position, condition in enumerate(order):
            trials.append(run_trial(seed, condition, position))

    by_pair = {}
    for trial in trials:
        by_pair.setdefault(trial["seed"], {})[trial["condition"]] = trial
    pair_results = []
    for seed in SEEDS:
        short = by_pair[seed]["short"]
        long = by_pair[seed]["long"]
        control_fields = (
            "sqlite_version", "journal_mode", "page_size", "synchronous",
            "wal_autocheckpoint", "reader_snapshot_count", "writes", "rows_per_write",
        )
        controls_match = all(short[k] == long[k] for k in control_fields)
        head_match = short["log_frames"] == long["log_frames"]
        wal_match = short["wal_bytes_before"] == long["wal_bytes_before"]
        valid = controls_match and head_match and wal_match
        pair_results.append({
            "seed": seed,
            "valid": valid,
            "controls_match": controls_match,
            "log_frames_match": head_match,
            "wal_bytes_match": wal_match,
            "short_checkpointed_frames": short["checkpointed_frames"],
            "long_checkpointed_frames": long["checkpointed_frames"],
            "delta_long_minus_short": long["checkpointed_frames"] - short["checkpointed_frames"],
            "short_checkpoint_duration_ms": short["checkpoint_duration_ms"],
            "long_checkpoint_duration_ms": long["checkpoint_duration_ms"],
        })

    valid_pairs = [p for p in pair_results if p["valid"]]
    negative = sum(p["delta_long_minus_short"] < 0 for p in valid_pairs)
    nonnegative = sum(p["delta_long_minus_short"] >= 0 for p in valid_pairs)
    if len(valid_pairs) >= 10 and negative >= 10:
        outcome = "age_penalty"
    elif len(valid_pairs) >= 10 and nonnegative >= 10:
        outcome = "no_age_penalty"
    else:
        outcome = "uncertain"

    differences = [p["delta_long_minus_short"] for p in valid_pairs]
    classification = {
        "frozen_rule": {
            "age_penalty": "at least 10 valid pairs and at least 10/12 valid-pair deltas < 0",
            "no_age_penalty": "at least 10 valid pairs and at least 10/12 valid-pair deltas >= 0",
            "uncertain": "fewer than 10 valid pairs, neither directional rule met, or controls fail",
        },
        "outcome_id": outcome,
        "pairs_total": len(pair_results),
        "pairs_valid": len(valid_pairs),
        "pairs_invalid": len(pair_results) - len(valid_pairs),
        "valid_negative_delta_count": negative,
        "valid_nonnegative_delta_count": nonnegative,
        "valid_delta_median": statistics.median(differences) if differences else None,
        "valid_pair_deltas": differences,
        "all_pair_results": pair_results,
    }
    (OUT / "raw_trials.json").write_text(json.dumps({
        "experiment_id": "E03",
        "sqlite_version": sqlite3.sqlite_version,
        "randomized_orders": orders,
        "trial_count": len(trials),
        "trials": trials,
    }, indent=2))
    (OUT / "classification.json").write_text(json.dumps(classification, indent=2))
    print(json.dumps({
        "trial_count": len(trials),
        "pairs_valid": classification["pairs_valid"],
        "outcome_id": outcome,
        "negative": negative,
        "nonnegative": nonnegative,
        "median_delta": classification["valid_delta_median"],
    }, indent=2))


if __name__ == "__main__":
    main()
