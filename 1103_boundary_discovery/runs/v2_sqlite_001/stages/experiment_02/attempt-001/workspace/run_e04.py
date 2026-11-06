from __future__ import annotations

import json
import random
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path


OUT = Path(__file__).parent
SEEDS = list(range(20261128, 20261140))
CONDITIONS = {"early": 0, "mid": 12, "late": 23}
WRITES = 24
ROWS_PER_WRITE = 10
SQL = "INSERT INTO sample(value) VALUES (?)"


def run_trial(seed: int, condition: str, position: int) -> dict:
    snapshot_prefix = CONDITIONS[condition]
    with tempfile.TemporaryDirectory(prefix="e04-") as td:
        db = Path(td) / "trial.sqlite"
        writer = sqlite3.connect(db, timeout=5)
        writer.execute("PRAGMA page_size=4096")
        journal_mode = writer.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        writer.execute("PRAGMA synchronous=NORMAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
        writer.commit()

        reader = sqlite3.connect(db, timeout=5)
        reader_opened_at_prefix = None
        snapshot_count = None
        commit_durations_ms = []
        transaction_events = []
        for batch in range(WRITES):
            if batch == snapshot_prefix:
                reader.execute("BEGIN")
                snapshot_count = reader.execute("SELECT count(*) FROM sample").fetchone()[0]
                reader_opened_at_prefix = batch
                transaction_events.append({
                    "event": "reader_snapshot",
                    "after_committed_batches": batch,
                    "visible_rows": snapshot_count,
                    "reader_transaction_active": reader.in_transaction,
                })
            values = [(f"{batch}:{row}",) for row in range(ROWS_PER_WRITE)]
            start = time.perf_counter_ns()
            writer.executemany(SQL, values)
            writer.commit()
            duration_ms = (time.perf_counter_ns() - start) / 1e6
            commit_durations_ms.append(duration_ms)
            transaction_events.append({
                "event": "write_commit",
                "batch_index": batch,
                "committed_batches": batch + 1,
                "rows": len(values),
                "duration_ms": duration_ms,
            })

        if snapshot_prefix == WRITES:
            reader.execute("BEGIN")
            snapshot_count = reader.execute("SELECT count(*) FROM sample").fetchone()[0]
            reader_opened_at_prefix = WRITES
            transaction_events.append({"event": "reader_snapshot", "after_committed_batches": WRITES,
                                       "visible_rows": snapshot_count,
                                       "reader_transaction_active": reader.in_transaction})

        wal_path = Path(f"{db}-wal")
        wal_bytes_before = wal_path.stat().st_size if wal_path.exists() else 0
        reader_active_before = reader.in_transaction
        checkpoint_start_ns = time.perf_counter_ns()
        checkpoint = list(writer.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone())
        checkpoint_ms = (time.perf_counter_ns() - checkpoint_start_ns) / 1e6
        wal_bytes_after = wal_path.stat().st_size if wal_path.exists() else 0

        result = {
            "seed": seed,
            "condition": condition,
            "order_position": position,
            "snapshot_prefix_batches": snapshot_prefix,
            "reader_snapshot_after_committed_batches": reader_opened_at_prefix,
            "reader_snapshot_visible_rows": snapshot_count,
            "reader_active_at_checkpoint": reader_active_before and reader.in_transaction,
            "sqlite_version": sqlite3.sqlite_version,
            "journal_mode": journal_mode,
            "page_size": writer.execute("PRAGMA page_size").fetchone()[0],
            "synchronous": writer.execute("PRAGMA synchronous").fetchone()[0],
            "wal_autocheckpoint": writer.execute("PRAGMA wal_autocheckpoint").fetchone()[0],
            "writes": WRITES,
            "rows_per_write": ROWS_PER_WRITE,
            "rows_committed": WRITES * ROWS_PER_WRITE,
            "transaction_events": transaction_events,
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
        order = list(CONDITIONS)
        random.Random(seed).shuffle(order)
        orders.append({"seed": seed, "order": order})
        for position, condition in enumerate(order):
            trials.append(run_trial(seed, condition, position))

    by_seed: dict[int, dict[str, dict]] = {}
    for trial in trials:
        by_seed.setdefault(trial["seed"], {})[trial["condition"]] = trial
    checks = []
    control_fields = (
        "sqlite_version", "journal_mode", "page_size", "synchronous",
        "wal_autocheckpoint", "writes", "rows_per_write", "rows_committed",
    )
    for seed in SEEDS:
        group = by_seed[seed]
        baseline = group["early"]
        controls_match = all(
            all(group[c][key] == baseline[key] for key in control_fields)
            for c in CONDITIONS
        )
        log_match = len({group[c]["log_frames"] for c in CONDITIONS}) == 1
        wal_match = len({group[c]["wal_bytes_before"] for c in CONDITIONS}) == 1
        prefix_match = all(
            group[c]["reader_snapshot_after_committed_batches"] == expected
            and group[c]["snapshot_prefix_batches"] == expected
            and group[c]["reader_snapshot_visible_rows"] == expected * ROWS_PER_WRITE
            for c, expected in CONDITIONS.items()
        )
        reader_active = all(group[c]["reader_active_at_checkpoint"] for c in CONDITIONS)
        valid = controls_match and log_match and wal_match and prefix_match and reader_active
        values = {c: group[c]["checkpointed_frames"] for c in CONDITIONS}
        checks.append({
            "seed": seed,
            "valid": valid,
            "controls_match": controls_match,
            "log_frames_match": log_match,
            "wal_bytes_before_match": wal_match,
            "snapshot_prefixes_match": prefix_match,
            "reader_active_all_conditions": reader_active,
            "checkpointed_frames": values,
            "late_minus_early": values["late"] - values["early"],
            "mid_at_least_early": values["mid"] >= values["early"],
            "all_three_equal": len(set(values.values())) == 1,
        })

    valid = [x for x in checks if x["valid"]]
    order_count = sum(x["late_minus_early"] > 0 for x in valid)
    mid_count = sum(x["mid_at_least_early"] for x in valid)
    flat_count = sum(x["all_three_equal"] for x in valid)
    if len(valid) >= 10 and order_count >= 10 and mid_count >= 10:
        outcome = "position_order"
    elif len(valid) >= 10 and flat_count >= 10:
        outcome = "position_flat"
    elif len(valid) < 10:
        outcome = "uncertain"
    else:
        outcome = "uncertain"

    durations = [t["checkpoint_duration_ms"] for t in trials]
    classification = {
        "frozen_rule": {
            "position_order": "至少10/12有效种子 late checkpointed_frames > early，且至少10/12 mid >= early",
            "position_flat": "至少10/12有效种子的 early/mid/late checkpointed_frames 完全相同",
            "uncertain": "有效种子少于10、控制不符、两类规则均未达到或出现其他形态",
        },
        "outcome_id": outcome,
        "seed_count": len(SEEDS),
        "valid_seed_count": len(valid),
        "invalid_seed_count": len(checks) - len(valid),
        "position_order_late_gt_early_count": order_count,
        "position_order_mid_ge_early_count": mid_count,
        "position_flat_count": flat_count,
        "valid_seed_results": checks,
        "checkpoint_duration_ms_median": statistics.median(durations) if durations else None,
        "checkpoint_duration_ms_min": min(durations) if durations else None,
        "checkpoint_duration_ms_max": max(durations) if durations else None,
    }
    raw = {
        "experiment_id": "E04",
        "requested_model": "GPT-6 Luna for research roles; this experimentalist stage uses Python/sqlite3 and no model inference",
        "sqlite_version": sqlite3.sqlite_version,
        "randomized_orders": orders,
        "trial_count": len(trials),
        "trials": trials,
    }
    (OUT / "raw_trials.json").write_text(json.dumps(raw, indent=2))
    (OUT / "classification.json").write_text(json.dumps(classification, indent=2))
    print(json.dumps({
        "trial_count": len(trials), "valid_seeds": len(valid), "outcome_id": outcome,
        "position_order_late_gt_early": order_count,
        "position_order_mid_ge_early": mid_count,
        "position_flat": flat_count,
        "checkpoint_ms_median": classification["checkpoint_duration_ms_median"],
        "checkpoint_ms_range": [classification["checkpoint_duration_ms_min"], classification["checkpoint_duration_ms_max"]],
    }, indent=2))


if __name__ == "__main__":
    main()
