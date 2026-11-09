# V2 Run Selection Review

## Assessment

The run shows functional research execution, but it has produced little resolution of the original useful question so far. It is not an agent-only proposal exercise: Luna planning stages read actual ledgers/results, E02 ran 72 fresh-database SQLite trials across three policies and two fixed trace shapes, and E03 ran 24 real SQLite trials. E02 directly tested whether a current reader-lifecycle policy improved PASSIVE scheduling cost against fixed-period and WAL-growth baselines. E03 followed with a controlled age intervention. These were actual measurements on SQLite 3.51.3, though both experiments remain confined to small, serialized local traces.

E02 is the most relevant experiment to the original gap. It used 12 randomized policy orders per shape, matched 240-row workloads, and measured checkpoint calls, timing, WAL state, and transaction latency. On its single held-out shape, lifecycle checkpoint time was not lower by the point estimate than either baseline (0.318 ms versus 0.297 and 0.300 ms); both paired cost intervals included zero. The result therefore demonstrates no lifecycle gain on H1, but it does not settle whether the baselines are sufficient on other schedule shapes. The frozen intervention defines one held-out shape while both decisive outcome classes require two. That internal mismatch makes the registered classification necessarily inconclusive. The 12 seeds randomize policy order over the same trace, not workload schedules. Serial replay also makes reader/writer delay different from concurrent service latency.

E03 cleanly ruled against the strong age-only penalty in its tested setting: all 12 paired runs had matching WAL head/size and exactly 2 of 26 frames checkpointed in both short- and long-age conditions. This is useful calibration against treating elapsed reader age as a proxy for checkpoint progress; it does not resolve the anchor question about scheduling across release/burst schedules. The ledger currently maps E03 as supporting B1's snapshot-position claim, but E03 held snapshot position fixed. B1 should remain untested; only the age-specific C3 prediction is contradicted.

Planner 02's selected E04 changes the reader's snapshot prefix and measures PASSIVE frame counts in the same small workload. That is a feasible calibration of the documented end-mark effect. SQLite's official WAL guide already explains that reader end marks constrain checkpoint progress, and the verified source is recorded in the scout folder. E04 is therefore primarily a mechanism reproduction, not new uncertainty resolution about policy value or telemetry sufficiency. It is planned, not executed, and the run remains `running` in `v2_state.json`.

## Selection Changes

1. Keep one plain-language anchor question in run state: whether the observable signals available to a practical checkpoint scheduler can improve cost under changing reader-release/write-burst schedules, or whether public telemetry has a useful limit. Tag each proposed action as `anchor test`, `calibration`, or `new branch`; this is routing context, not a score.
2. Allow calibration when it checks an implementation or measurement assumption that could invalidate the anchor experiment, or when its result changes the next action. Require the planner to say which assumption it checks and what each result would change. After a calibration, return selection to the anchor question unless the calibration exposed a concrete blocker or invalid premise. This preserves useful controls without letting repeated known-effect checks consume every remaining slot.
3. Before freezing a plan, compare its outcome-class requirements with its intervention. Here, a plan specifying one held-out shape cannot require two for either decisive class. Revise the plan before execution or make its registered conclusion honestly single-shape and exploratory.
4. Before mapping evidence to a ledger claim, check that the experiment varied the claim's distinguishing quantity. A measurement can refute an age proxy without supporting a separate snapshot-position relation. Keep that applicability check in the ordinary review, not as a numeric gate.
5. When a result is inconclusive, compare the next action against the anchor by stating what decision the result can change. E04 has high calibration value but low anchor value; a corrected policy comparison on a genuinely different held-out trace has higher anchor value. No scalar utility rubric is needed.

These changes do not forbid reproducing known behavior. They make its purpose explicit, preserve it when it is a useful prerequisite, and keep the run's limited experiments connected to the open research question.

## Evidence Read

- `runs/v2_sqlite_001/v2_state.json`: current status, hypotheses, E02/E03 observations and ledger mappings.
- `runs/v2_sqlite_001/frozen_plans/00_E02.json` and `01_E03.json`: pre-execution interventions and outcome classes.
- `runs/v2_sqlite_001/stages/experiment_00/attempt-001/workspace/report_zh.md`, `preregistration.md`, `classification.json`, `run_e02.py`, and `raw_trials.json`: E02 design, execution, mismatched holdout requirement, results, and implementation.
- `runs/v2_sqlite_001/stages/experiment_01/attempt-001/workspace/report_zh.md`, `classification.json`, `run_e03.py`, and `raw_trials.json`: E03 design and raw paired values.
- `runs/v2_sqlite_001/stages/plan_00/attempt-001/workspace/result.json`, `plan_01/.../result.json`, and `plan_02/.../result.json` plus plan reports: actual experiment selection reasoning. Plan 02 selected E04; no E04 result exists in the inspected run.
- `bootstrap/v2_scout/sources_verified/wal.txt`, `checkpoint.txt`, and `sources.json`: fetched SQLite documentation establishing the end-mark/checkpoint behavior as known prior work.
