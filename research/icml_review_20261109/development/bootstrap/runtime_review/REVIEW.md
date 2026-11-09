# Runtime Review

Reviewed `src/runtime.py` and `src/discover.py` after the v2 reliability changes. Validation used an offline fake Codex executable and temporary directories under this folder; it did not call a real model or access `runs/pilot_001`. The earlier pre-v2 results are retained in `fake_check_results.json`; current-source reruns are in `fake_check_results_v2.json`, driven by `fake_runtime_checks.py`.

## Findings

### Protocol decision errors need explicit repair

`discover.py` saves the coordinator result in `discovery_state.json` at lines 134-145 before validating the action object's required `role` and `task` fields at lines 157-163. The fake coordinator returned a structurally valid `dispatch` with `next_actions: [{}]`. The first run failed with `KeyError: 'role'`; resuming with identical arguments failed the same way, with one saved decision, zero completed actions, and no coordinator rerun. The original coordinator JSON remains intact, which is preferable to silently rewriting it, but there is no built-in repair route. An operator must make an explicit, versioned state/decision repair or start a new run while preserving the original output.

A `complete`/`blocked` result without a nonempty `REPORT.md` now leaves the pipeline `running` and exits with an error (`discover.py:146-150`). Repeating the same command reuses the saved coordinator decision and remains incomplete. The fake test then added the missing report as an explicit repair; the same command completed and the coordinator `result.json` hash remained unchanged. A repair action should stay explicit and preserve the original model output.

### Scope of runtime success

The runtime now rejects missing keys, empty summaries, wrong collection types, empty artifact lists, and artifact paths absent from the project (`runtime.py:259-285`). It marks a stage successful when the process exits normally and the structured stage result passes those checks. That is a pipeline-stage status, not a finding that an idea is scientifically correct or novel; the coordinator protocol remains responsible for research judgment. No scientific acceptance criteria were added to runtime.

The artifact check accepts a listed existing file anywhere in the project. Treat the list as a review locator, not as proof that the stage created new work. This is a quality convention to supervise in the research review, not a requirement that every role write new scientific code.

## v2 checks

- Dependency fingerprinting passed with a dependency record that has no `id`; the fingerprint now pairs records with the IDs from `stage.depends_on` (`runtime.py:128-136`). The generic dependency path is fixed. `discover.py` currently dispatches one stage per runtime config with no dependencies, so this defect did not affect its ordinary stages.
- A fake subprocess failure followed by a successful call resumed with the identical config. Attempt 1 failed, attempt 2 succeeded, and the manifest retained both attempts.
- A fake parent that exits on SIGTERM spawned a child that ignored SIGTERM and would write a marker after one second. The v2 timeout path killed the process group before the marker was written (`runtime.py:148-163`).
- Malformed stage result fields now produce `status=incomplete` and a nonzero runtime exit rather than `success`.
- A coordinator claiming completion without `REPORT.md` stays incomplete. Same-config retry alone does not change the bad result; explicit report repair recovers while preserving the original `result.json`.
- An invalid coordinator dispatch remains a repeated failure on same-config resume. This is the principal remaining recovery limitation.

## Input and permission boundaries

- Runtime inputs are resolved strictly, then constrained to regular files inside the project (`runtime.py:80-92`). A symlink targeting outside the project resolves outside and is rejected. A symlink targeting an internal file resolves to that file and is accepted; the later `is_symlink()` check sees the resolved target rather than the original link.
- The Codex process runs with `workspace-write` rooted at the assigned stage workspace. When present, `.venv` is also added with `--add-dir` (`runtime.py:231-239`), so its write protection depends on Codex CLI semantics rather than the prompt's instruction to write only to the attempt workspace. The model prompt's ban on credential access is not independently tested as an OS-level denial.
- `discover.py` enables network access in every generated stage config (`discover.py:45-52`). The prompt limits retrieval to public material, but the configuration itself does not impose host-level allowlisting.

## Test boundary

These checks establish runner behavior for the tested fake cases only. They do not establish that a real Codex child process obeys the prompt, that the current pilot's outputs are scientifically sound, or that the same timeout behavior has been observed against a live model process. No source or pilot run artifact was changed by this review.

