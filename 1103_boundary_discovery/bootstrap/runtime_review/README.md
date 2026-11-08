# Runtime Review Artifacts

`REVIEW.md` records the bounded source review and v2 reliability checks. `fake_check_results.json` is the pre-v2 baseline; `fake_check_results_v2.json` contains the current-source rerun. `fake_runtime_checks.py` is the offline fake CLI harness for those checks.

## Final Recovery Regression

`final_regression.py` uses a deterministic fake Codex CLI to run two same-config resume cases: an invalid coordinator dispatch on attempt 1, and a final decision missing `REPORT.md` on attempt 1. In both cases the runtime marks attempt 1 incomplete, `discover.py` caches no decision, and attempt 2 can return a valid `complete` result with a nonempty report. Both attempt completion records remain available. Results are recorded in `FINAL_REGRESSION.json`.

These checks use temporary directories under this folder. They do not call a model, read or write `runs/pilot_001`, or edit source files.
