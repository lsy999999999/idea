# Seed A independent proposal

## Scope

Prompt-level proposals from the assigned brief, scout code/results, and verified SQLite documentation. No new experiment or broad literature search was performed. The scout pair is development evidence: with 2,400 matched rows and 143 log frames, equal 589,192-byte WAL files and `busy=0` accompanied checkpoint counts of 143 without a reader and 2 with a held reader. The run does not measure timing policy performance.

## A1: A reader-pinned frame frontier bounds immediate progress

The smallest mechanistic state for a single PASSIVE attempt is the gap between the WAL head and the oldest active reader's snapshot end mark. A large WAL can be almost entirely checkpointable or mostly pinned, so WAL bytes and `busy=0` collapse cases with different immediate progress. This is a documented SQLite mechanism, not a new claim.

Measure reader transaction start relative to a controlled committed-write prefix and release time from the replay trace, alongside the actual PASSIVE `(busy, log_frames, checkpointed_frames)` result and WAL bytes. Use matched total rows, commit boundaries, and frame count. Do not read the predicted checkpoint result to construct the reader-state input. Prediction: at the same log head and with the same PASSIVE action, a snapshot opened before most writes will yield fewer newly checkpointed frames than one opened after most writes. The scout's no-reader/held-reader pair is directionally consistent, but it did not vary snapshot position or replicate.

Strong alternative: the difference is not reader position itself but another condition that covaried with reader presence, such as writer/checkpointer overlap or measurement noise. The existing result cannot distinguish these.

## A2: The timing of reader release changes the value of waiting

For scheduling across repeated attempts, current aggregate checkpoint telemetry may describe the pinned work but omit whether a useful release window is near. Two states with the same WAL head, checkpointed count, busy flag, and recent write rate may call for different next-attempt times if the oldest reader releases immediately in one trace and remains open through the next write burst in the other. This is a proposed workload-level timing relation, not an inferred SQLite hidden variable or a known release predictor.

Measure reader ages and scheduled release events from the controlled trace, and score the next fixed-horizon PASSIVE attempt by frames advanced and elapsed call time; separately count attempts and report reader and commit completion latency. Prediction: conditional on matching current public telemetry and upcoming writes, an attempt just after release advances more frames per call-time than an otherwise matched attempt before release. A policy using only telemetry available at decision time cannot exploit a release event it is not told; transaction age/history is a candidate public application signal to test, not assumed sufficient.

Strong alternative: the release schedule adds no useful predictive signal after the periodic or WAL-size baseline is matched for completion and service costs; any apparent gain is due to extra calls, trace alignment, or leaving more work outstanding. The experiment must charge each PASSIVE call and compare completion/progress, not WAL file allocation alone.

## Candidate next discriminator

Replay matched write traces with readers opened at different controlled write prefixes and released either before or after a prespecified checkpoint opportunity. Match public telemetry at the decision point where feasible; randomize policy/condition order on fresh databases. First test whether snapshot position explains immediate progress (A1); then test whether release timing improves a fixed-horizon scheduler after conditioning on observed telemetry (A2). Preserve an uncertain class. No threshold or performance effect size is claimed from the scout.

## Closest checked prior work

SQLite's WAL guide documents that reader end marks can stop checkpoint progress and describes the automatic checkpoint threshold and frequency tradeoff. The checkpoint API documents PASSIVE behavior and log/checkpointed frame counts. The PRAGMA reference documents the WAL checkpoint interface and returned counters. These sources explain A1 and define observable telemetry; they do not establish A2's scheduling benefit. This pass is not a dedicated literature novelty review.
