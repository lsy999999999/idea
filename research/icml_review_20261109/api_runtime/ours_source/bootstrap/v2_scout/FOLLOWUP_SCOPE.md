# Follow-up Scope: Checkpoint Scheduling Under Changing Workloads

## Documented boundary

Do not investigate whether long readers can limit WAL checkpoint progress: SQLite documents that behavior. In its WAL guide, SQLite says checkpoints may run alongside readers but stop at WAL content beyond a current reader's end mark, and that long read transactions can prevent progress. It also describes the default automatic PASSIVE checkpoint after the WAL exceeds about 1,000 pages, and the tradeoff between frequent checkpointing (read performance) and infrequent checkpointing (write performance). The checkpoint API documentation specifies that PASSIVE does not wait for readers or writers and may leave a checkpoint unfinished. Verified copies and retrieval metadata are in `sources_verified/wal.txt`, `sources_verified/checkpoint.txt`, and `sources_verified/sources.json`.

## Residual question

Across changing but replayable reader-release and write-burst schedules, is SQLite's public checkpoint telemetry sufficient to time useful PASSIVE checkpoint attempts with lower total coordination cost than a simple periodic or WAL-size-triggered baseline? Or can two workload states with the same telemetry require materially different next actions? Treat either a reproducible policy gain or a precise telemetry counterexample as informative; the experiment must let the evidence determine which, if either, occurs. This is an implementation-scoped software question, not a claim of algorithm novelty.

## Minimal executable study

Use the installed SQLite library through Python `sqlite3` with a real temporary WAL database and two or more client connections. Replay a small prewritten workload trace containing matched writes and multiple reader snapshot start/release times, including short and long reads and bursts separated by quiet intervals. Compare the SQLite default size-triggered behavior and a fixed periodic PASSIVE schedule with at most one simple alternative based on observations available through stock PRAGMAs/API. Keep transaction contents and arrival/release traces identical across policies. Avoid a synthetic outcome model: every checkpoint, commit, read, and result must come from SQLite execution.

Record per attempt: public checkpoint return/telemetry (`busy`, log frames, checkpointed frames), WAL bytes, call duration, and frames advanced. Record per transaction: commit latency and completion time; record each reader's transaction duration and completion. Aggregate checkpoint calls, zero/low-progress calls, elapsed checkpoint time, peak WAL bytes, total and tail commit latency, and reader completion delay. A WAL file that remains allocated after checkpoint is not by itself evidence of unfinished checkpoint work.

## Competing accounts to retain

- A fixed period or WAL-size trigger already captures the useful workload variation; more involved timing does not reduce cost after matching checkpoint completion and reader/writer service.
- Reader-release and write-burst ordering changes whether an attempt advances or blocks, and information in available runtime observations can improve scheduling on unseen traces.
- Public aggregate telemetry cannot distinguish at least some states that have different near-term checkpoint outcomes; a counterexample would bound what a telemetry-only policy can achieve.

These are alternatives to test, not conclusions or required mechanisms. Do not name a proposed hidden state in advance.

## Cost and fairness constraints

Match total committed rows, transaction boundaries, reader arrival/release schedules, durability settings, SQLite build, page size, filesystem, and trace order across compared policies. Randomize policy order on fresh databases. Require the policy comparison to report checkpoint completion/progress alongside cost; a policy does not win by leaving more WAL work outstanding. Report reader and writer latency distributions separately. Reject a gain that comes with worse reader completion or materially worse writer tail latency unless the tradeoff is explicitly stated. Keep checkpoint mode and busy timeout the same for the primary comparison; do not mix a blocking FULL/RESTART policy into the primary PASSIVE comparison.

## Exploration and held-out separation

Use a short trace only to debug instrumentation and shape candidate schedules. Before policy comparison, write down the predicted contrast and aggregate measures. Hold out at least one reader-release/write-burst schedule shape, not merely new random seeds from the same trace, and run it on fresh databases. A second SQLite version is replication. This remains evidence about the tested SQLite build, local filesystem, trace family, and settings; it does not establish production benefit or a new database algorithm.

## Source evidence

- SQLite, “Write-Ahead Logging,” <https://www.sqlite.org/wal.html>, fetched HTTP 200 on 2026-11-03; local copy `sources_verified/wal.txt`. Relevant passages: reader end marks can limit checkpoint progress; default automatic threshold is about 1,000 pages; frequent checkpoints trade read performance against write performance.
- SQLite, “Checkpoint a database,” <https://www.sqlite.org/c3ref/wal_checkpoint_v2.html>, fetched HTTP 200 on 2026-11-03; local copy `sources_verified/checkpoint.txt`. Relevant passages: PASSIVE does not wait and may be incomplete; API exposes log and checkpointed frame counts.
- SQLite, “PRAGMA Statements,” <https://www.sqlite.org/pragma.html>, fetched HTTP 200 on 2026-11-03; local copy `sources_verified/pragma.txt`. Relevant passages: default autocheckpoint interval is 1,000 pages; `wal_checkpoint` returns busy status, log frames, and checkpointed frames.

These are implementation documentation, not a survey of scheduler research. Literature positioning remains open and must be checked before making any novelty claim.
