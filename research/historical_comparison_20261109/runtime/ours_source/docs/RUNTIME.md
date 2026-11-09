# Research Runtime

`src/runtime.py` runs ordered, resumable research stages through the already authenticated Codex CLI. It uses only Python's standard library and does not read authentication files.

## Configuration

Save a JSON config inside this project. `run_dir` is relative to the project root unless absolute, and must remain inside the project. Input paths are project-relative by default; absolute inputs are accepted only when they resolve inside the project.

```json
{
  "model": "gpt-6-luna",
  "reasoning_effort": "high",
  "run_dir": "runs/first_probe",
  "network_access": false,
  "stages": [
    {
      "id": "scan",
      "role": "researcher",
      "prompt": "Inspect the provided material and identify a testable open question.",
      "inputs": ["README.md"],
      "timeout_s": 1800
    },
    {
      "id": "analysis",
      "role": "analyst",
      "prompt": "Develop and assess the question using available project evidence.",
      "inputs": ["README.md"],
      "timeout_s": 3600,
      "depends_on": ["scan"]
    }
  ]
}
```

Each stage requires `id`, `role`, `prompt`, `inputs`, and `timeout_s`. Stages run in list order. Optional `depends_on` names earlier stages, and `network_access: true` enables the CLI's workspace-write network option for that stage. Each attempt workspace contains only `AGENTS.md` and a snapshot of `src/runtime.py`; input files retain their original project paths and are read in place. Roles can read the original project and shared run directory but are instructed to write new artifacts only in their assigned workspace. When `.venv` exists, the CLI receives it as an additional project path so roles can use its installed packages without copying the environment into each attempt.

## Run and inspect

```sh
python3 src/runtime.py --config path/to/run.json
python3 src/runtime.py --config path/to/run.json --stage scan
python3 src/runtime.py --config path/to/run.json --status
```

Every attempt gets a new `runs/<run>/stages/<id>/attempt-NNN/` directory. The CLI's JSONL events, stderr, final message, and `result.json` are preserved there. A stage is successful only when the CLI exits zero and `result.json` is valid JSON containing at least `summary`, `artifacts`, `evidence`, `claims`, `limitations`, and `next_actions`; coordinator-specific fields are allowed. A completed attempt is skipped on resume only when its input/dependency hash and output tree hash still match. Otherwise the next attempt uses a fresh directory.

The run-level `manifest.json` records requested model and reasoning effort, CLI version, status, timestamps, exit code, timeout, hashes, paths, and usage events exposed by the CLI. `events.jsonl` is append-only and records stage starts, finishes, skips, and dependency blocks. A timeout terminates the CLI process group. `--stage` runs only the named stage; its dependencies must already have successful manifest entries.
