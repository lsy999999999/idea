# Bridge synthesis: WAL checkpoint progress and scheduling

## Comparative reading

The two seed contributions agree on the immediate mechanism. A1/B1 describe SQLite's documented reader end-mark constraint: at a fixed WAL head, the oldest active reader snapshot can limit how far a PASSIVE checkpoint advances. The scout's single paired observation (143/143 frames without a held reader versus 2/143 with one, both `busy=0` and 589,192 WAL bytes) is compatible with this account, but does not isolate snapshot position or establish repeatability.

A2 and B2 are compatible extensions, not competing mechanisms. Both ask whether histories collapsed into aggregate telemetry can imply different near-term checkpoint opportunities because reader lifecycle/release timing is omitted. Neither has evidence of matched decision histories, an observability counterexample, or net policy benefit. Reader age is not itself a substitute for snapshot end-mark position, and future release time cannot be used as a policy input unless it is available at decision time.

## Retrieved sources (2026-11-04 UTC)

- SQLite, [Write-Ahead Logging](https://www.sqlite.org/wal.html), retrieved live (HTTP content returned). It explains that each reader has an end mark and that checkpoint progress cannot pass pages needed by active readers. This makes the proposed immediate constraint known SQLite behavior.
- SQLite, [Checkpoint a database](https://www.sqlite.org/c3ref/wal_checkpoint_v2.html), already present as an HTTP-200 verified project copy. PASSIVE does not wait for readers/writers and may leave work incomplete; frame counters provide the relevant operation result.
- Zhu, Hu, and Wang, [Asynchronous and Adaptive Checkpoint for WAL-based Data Storage Systems](https://doi.org/10.1109/icpads60453.2023.00179), 2023 ICPADS. Retrieved OpenAlex record W4393207694 and Crossref DOI metadata/abstract. The abstract describes SQLite WAL, asynchronous fsync, and online checkpoint-frequency adjustment based on read/write requests, reporting up to 92.3% lower write tail latency. This is a direct prior-art baseline for adaptive/load-aware frequency. The paper is closed access in OpenAlex and its full text was not reviewed; the abstract does not settle whether it models active-reader end marks or the proposed timing question.
- PostgreSQL, [Routine Vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html), live documentation retrieved (PostgreSQL 18). It describes MVCC vacuum as reclaiming obsolete row versions only when no transaction can still see them, and recommends ending long-running transactions in wraparound recovery. This is a cross-domain analogue of deferred maintenance bounded by active transaction visibility. It is not evidence that PostgreSQL and SQLite checkpoint semantics or optimal policies are equivalent.

## What can be distinguished

There is no justified new C1/C2 representation here: end-mark/head state is already explicit in SQLite's model, and the seed materials do not show that exposing it to a scheduler improves outcomes. Keep proposals empty.

The useful measurable contrast is conditional and staged. First hold build, writes, commit boundaries, WAL head, and checkpoint mode fixed while varying only the reader's snapshot prefix; record the pre-action trace-derived snapshot position separately from `(busy, log_frames, checkpointed_frames)`. This distinguishes end-mark position from reader duration/reader presence and other co-varying conditions. Then, only if this replicates, compare release-timing strata at matched decision-time public telemetry. Freeze a policy-visible feature set; treat actual future release events as diagnosis only. Compare fixed-period, WAL-size, and request-rate (Walack-like) triggers against any proposed age/history signal on fresh, held-out release/burst shapes, charging each checkpoint attempt and reporting completed frames, checkpoint time/calls, remaining work, reader completion latency, and commit tail latency. If telemetry histories cannot be matched before actions, do not call the result an observability counterexample.

No scientific experiment was run in this bridge stage. No new mechanism, strategy gain, or novelty claim is supported. The immediate SQLite behavior is documented; the scheduling extension remains an untested, potentially useful question.
