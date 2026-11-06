# V2 Scout: SQLite WAL Checkpoint Behavior

## Phenomenon and question

SQLite's write-ahead log can accumulate while a database is active. A useful, narrow question is whether checkpoint progress and commit cost under a fixed write workload are better predicted by (a) the amount of logged data or (b) the age and position of a concurrent reader's snapshot. These explanations can be separated by holding writes fixed and intervening on reader lifetime, then varying write batch size and the reader's snapshot position.

This is a question about measured SQLite behavior in the named local environment. It does not posit or recover a hidden mechanism, and a small probe is not a general database benchmark.

## Independently measurable outcome

Record SQLite version, per-commit latency, WAL file bytes, and `PRAGMA wal_checkpoint(PASSIVE)`'s `(busy, log_frames, checkpointed_frames)` tuple. Repeat checkpoint measurements after ending the reader and requesting `TRUNCATE`. These are direct outcomes from the real SQLite implementation and filesystem, not generated labels. In the preliminary pair, both cases logged 143 frames and produced a 589,192-byte WAL. The no-reader case checkpointed 143 frames; the reader case checkpointed 2 while both returned `busy=0`. After ending the reader, `TRUNCATE` reduced the WAL file to zero bytes. The single-run commit latencies do not support an inference about performance.

## Executable environment and preliminary measurement

Run from the project root with `.venv/bin/python bootstrap/v2_scout/wal_checkpoint_probe.py`. The script creates temporary SQLite databases, disables automatic checkpointing, and compares a fixed sequence of 120 committed batches of 20 rows with and without a reader transaction opened before the writes. See `result.json` for the measured run. The only dependency is Python's standard-library `sqlite3` module.

## Allowed interventions

- Reader snapshot timing and duration, including no reader, a reader begun before writes, and a reader begun after a selected write prefix.
- Rows per transaction and number of commits, while keeping total inserted rows fixed in paired conditions.
- WAL autocheckpoint threshold and explicit checkpoint mode (`PASSIVE`, `FULL`, `RESTART`, `TRUNCATE`), one factor at a time.
- Repeat runs with fresh temporary databases and randomized condition order.

Do not infer production reliability from this local probe. Keep writer workload, SQLite version, journal settings, filesystem, and timing method in the report. Predeclare any comparison before later held-out runs.

## Nearby prior work and retrieval status

- SQLite, “Write-Ahead Logging”: <https://www.sqlite.org/wal.html>. The page is the closest implementation documentation for WAL, checkpointing, and reader interactions. A direct fetch was attempted on 2026-11-04 but failed because this environment could not resolve `www.sqlite.org`; no page text is claimed as fetched.
- SQLite, “PRAGMA Statements”: <https://www.sqlite.org/pragma.html#pragma_wal_checkpoint>. This documents checkpoint interfaces and result fields. Direct fetch was attempted on 2026-11-04 and failed for the same DNS restriction.
- OpenAlex query used as a nearby-work lead: <https://api.openalex.org/works?search=SQLite%20WAL%20checkpoint%20starvation%20reader&per-page=8&select=title,publication_year,doi,id>. Direct fetch failed because this environment could not resolve `api.openalex.org`; no search result is treated as evidence.

The installed runtime provides executable evidence about the tested SQLite build, but the literature screen remains outstanding. Do not claim novelty. The next researcher should fetch and read the cited documents and search primary literature before promoting a gap claim.

## Exploration and held-out distinction

The included run is development exploration: one fixed workload, one reader timing, one local SQLite build, and an immediate paired comparison. It is not a held-out test. For a follow-up, save the predicted contrast and analysis first, then use fresh databases and a preselected workload/reader-timing condition not used to formulate the contrast. A second SQLite version or filesystem is a separate replication, not a substitute for independent workload holdout.
