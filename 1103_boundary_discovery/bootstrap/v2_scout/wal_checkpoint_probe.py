"""Small, reproducible SQLite WAL checkpoint probe."""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path


def run_case(hold_reader: bool, writes: int = 120, rows_per_write: int = 20) -> dict:
    with tempfile.TemporaryDirectory(prefix="wal-probe-") as tmp:
        db_path = Path(tmp) / "probe.sqlite"
        writer = sqlite3.connect(db_path, timeout=5)
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        writer.commit()

        reader = sqlite3.connect(db_path, timeout=5) if hold_reader else None
        if reader is not None:
            reader.execute("BEGIN")
            reader.execute("SELECT count(*) FROM sample").fetchone()

        commit_ms = []
        for batch in range(writes):
            start = time.perf_counter_ns()
            writer.executemany(
                "INSERT INTO sample(value) VALUES (?)",
                [(f"{batch}:{i}",) for i in range(rows_per_write)],
            )
            writer.commit()
            commit_ms.append((time.perf_counter_ns() - start) / 1e6)

        wal_path = Path(f"{db_path}-wal")
        wal_bytes_before = wal_path.stat().st_size if wal_path.exists() else 0
        checkpoint_before_close = writer.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
        wal_bytes_after_passive = wal_path.stat().st_size if wal_path.exists() else 0

        if reader is not None:
            reader.rollback()
            reader.close()
        checkpoint_after_close = writer.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        wal_bytes_after_truncate = wal_path.stat().st_size if wal_path.exists() else 0
        result = {
            "hold_reader": hold_reader,
            "writes": writes,
            "rows_per_write": rows_per_write,
            "rows_total": writes * rows_per_write,
            "wal_bytes_before_checkpoint": wal_bytes_before,
            "passive_checkpoint_busy_log_checkpointed": checkpoint_before_close,
            "wal_bytes_after_passive": wal_bytes_after_passive,
            "truncate_checkpoint_after_reader_close": checkpoint_after_close,
            "wal_bytes_after_truncate": wal_bytes_after_truncate,
            "commit_ms_median": sorted(commit_ms)[len(commit_ms) // 2],
            "commit_ms_p95": sorted(commit_ms)[int(len(commit_ms) * 0.95) - 1],
        }
        writer.close()
        return result


if __name__ == "__main__":
    cases = [run_case(False), run_case(True)]
    print(json.dumps({"sqlite_version": sqlite3.sqlite_version, "cases": cases}, indent=2))
