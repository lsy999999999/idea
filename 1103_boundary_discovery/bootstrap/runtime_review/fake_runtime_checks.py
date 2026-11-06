#!/usr/bin/env python3
"""Offline checks for runtime edge cases. Uses only a fake Codex executable."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile


PROJECT = Path(__file__).resolve().parents[2]
EXISTING_PROJECT_FILE = str(Path(__file__).resolve().relative_to(PROJECT))
sys.path.insert(0, str(PROJECT / "src"))
import runtime  # noqa: E402


def check_dependency_fingerprint() -> dict:
    try:
        runtime.stage_input_fingerprint(
            {"id": "child", "depends_on": ["parent"]}, [],
            [{"status": "success", "output_sha256": "a" * 64}], "fake", "low")
    except KeyError as exc:
        return {"check": "dependency_fingerprint", "observed": f"KeyError: {exc}",
                "confirmed": True,
                "meaning": "A normal manifest stage record lacks id, so a dependent stage cannot fingerprint it."}
    return {"check": "dependency_fingerprint", "observed": "no error", "confirmed": True,
            "meaning": "Fingerprinting uses declared dependency IDs paired with manifest records."}


def check_shape_only_success(root: Path) -> dict:
    case = root / "shape_only"
    case.mkdir()
    fake = case / "codex-fake"
    fake.write_text("""#!/usr/bin/env python3
import json, pathlib, re, sys
if '--version' in sys.argv:
    print('fake-codex 0')
    raise SystemExit(0)
args = sys.argv
path = pathlib.Path(args[args.index('--output-last-message') + 1])
path.write_text('fake final response\\n')
prompt = sys.stdin.read()
match = re.search(r'Before finishing, write valid JSON to this path:\\n([^\\n]+)', prompt)
pathlib.Path(match.group(1)).write_text(json.dumps({
    'summary': '', 'artifacts': None, 'evidence': 'not evidence', 'claims': {},
    'limitations': None, 'next_actions': {'not': 'a list'}
}))
""", encoding="utf-8")
    fake.chmod(0o755)
    run_dir = case / "run"
    config = case / "config.json"
    config.write_text(json.dumps({
        "codex_bin": str(fake), "run_dir": str(run_dir),
        "stages": [{"id": "s1", "role": "fake", "prompt": "fake", "inputs": [], "timeout_s": 5}],
    }), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(PROJECT / "src/runtime.py"), "--config", str(config)],
                          cwd=PROJECT, capture_output=True, text=True, timeout=15)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["stages"]["s1"]
    result_path = run_dir / "stages" / "s1" / "attempt-001" / "workspace" / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    confirmed = proc.returncode != 0 and record["status"] == "incomplete" and record["result_path"] is None
    return {"check": "reject_malformed_stage_result", "runtime_exit_code": proc.returncode,
            "runtime_status": record["status"], "malformed_artifacts_value": result["artifacts"],
            "confirmed": confirmed,
            "meaning": "Malformed required fields no longer count as a normally completed stage."}


def check_timeout_kills_process_group(root: Path) -> dict:
    case = root / "timeout_group"
    case.mkdir()
    pid_path = case / "child.pid"
    marker_path = case / "child-survived.txt"
    child_code = (
        "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"open({str(pid_path)!r}, 'w').write(str(__import__('os').getpid())); time.sleep(1.0); "
        f"open({str(marker_path)!r}, 'w').write('survived')"
    )
    parent_code = (
        "import subprocess,sys,time; "
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}]); time.sleep(20)"
    )
    stdout, stderr = case / "stdout", case / "stderr"
    returncode, timed_out, _, _ = runtime.run_process(
        [sys.executable, "-c", parent_code], case, "", 0.25, stdout, stderr)
    pid = int(pid_path.read_text(encoding="utf-8")) if pid_path.exists() else None
    import time
    time.sleep(1.1)
    survived = marker_path.exists()
    return {"check": "timeout_process_group", "returncode": returncode, "timed_out": timed_out,
            "grandchild_pid_recorded": pid is not None, "grandchild_survived_runner_return": survived,
            "confirmed": timed_out and not survived,
            "meaning": "Timeout cleanup kills the original process group even after its leader exits on SIGTERM."}


def check_invalid_dispatch_resume(root: Path) -> dict:
    case = root / "invalid_dispatch"
    fakebin = case / "fakebin"
    fakebin.mkdir(parents=True)
    fake = fakebin / "codex"
    fake.write_text("""#!/usr/bin/env python3
import json, pathlib, re, sys
if '--version' in sys.argv:
    print('fake-codex 0')
    raise SystemExit(0)
args = sys.argv
last = pathlib.Path(args[args.index('--output-last-message') + 1])
last.write_text('fake response\\n')
prompt = sys.stdin.read()
result_path = re.search(r'Before finishing, write valid JSON to this path:\\n([^\\n]+)', prompt).group(1)
result = {'summary': 'malformed task dispatch', 'artifacts': [__ARTIFACT__],
          'evidence': [], 'claims': [], 'limitations': [], 'next_actions': [{}],
          'decision': 'dispatch', 'research_status': 'dispatch', 'candidate': None}
pathlib.Path(result_path).write_text(json.dumps(result))
""".replace("__ARTIFACT__", json.dumps(EXISTING_PROJECT_FILE)), encoding="utf-8")
    fake.chmod(0o755)
    brief = case / "brief.md"
    brief.write_text("fake brief\n", encoding="utf-8")
    run = case / "run"
    env = dict(os.environ)
    env["PATH"] = str(fakebin) + os.pathsep + env.get("PATH", "")
    command = [sys.executable, str(PROJECT / "src/discover.py"), "--brief", str(brief),
               "--run-dir", str(run), "--max-actions", "1"]
    first = subprocess.run(command, cwd=PROJECT, env=env, capture_output=True, text=True, timeout=20)
    second = subprocess.run(command, cwd=PROJECT, env=env, capture_output=True, text=True, timeout=20)
    state = json.loads((run / "discovery_state.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    stuck = (first.returncode != 0 and second.returncode != 0 and len(state["decisions"]) == 1
             and len(state["actions"]) == 0 and len(manifest["stages"]) == 1)
    return {"check": "invalid_dispatch_resume", "first_exit_code": first.returncode,
            "second_exit_code": second.returncode,
            "first_error": first.stderr.splitlines()[-1] if first.stderr else "",
            "second_error": second.stderr.splitlines()[-1] if second.stderr else "",
            "saved_decisions": len(state["decisions"]), "completed_actions": len(state["actions"]),
            "coordinator_stages": len(manifest["stages"]), "confirmed": stuck,
            "meaning": "A malformed dispatch is persisted as a decision before validation; resume reuses it and fails identically without rerunning the coordinator or exposing a recovery path."}


def check_retry_same_config(root: Path) -> dict:
    case = root / "retry_same_config"
    case.mkdir()
    counter = case / "invocations.txt"
    fake = case / "codex-fake"
    fake.write_text("""#!/usr/bin/env python3
import json, pathlib, re, sys
if '--version' in sys.argv:
    print('fake-codex 0')
    raise SystemExit(0)
count_path = pathlib.Path(__COUNTER__)
count = int(count_path.read_text()) + 1 if count_path.exists() else 1
count_path.write_text(str(count))
if count == 1:
    raise SystemExit(2)
args = sys.argv
pathlib.Path(args[args.index('--output-last-message') + 1]).write_text('ok\\n')
prompt = sys.stdin.read()
result_path = re.search(r'Before finishing, write valid JSON to this path:\\n([^\\n]+)', prompt).group(1)
pathlib.Path(result_path).write_text(json.dumps({
    'summary': 'retry succeeded', 'artifacts': [__ARTIFACT__], 'evidence': [], 'claims': [],
    'limitations': [], 'next_actions': []
}))
""".replace("__COUNTER__", repr(str(counter))).replace(
    "__ARTIFACT__", json.dumps(EXISTING_PROJECT_FILE)), encoding="utf-8")
    fake.chmod(0o755)
    run = case / "run"
    config = case / "config.json"
    config.write_text(json.dumps({"codex_bin": str(fake), "run_dir": str(run),
                                  "stages": [{"id": "s1", "role": "fake", "prompt": "fake",
                                              "inputs": [], "timeout_s": 5}]}), encoding="utf-8")
    command = [sys.executable, str(PROJECT / "src/runtime.py"), "--config", str(config)]
    first = subprocess.run(command, cwd=PROJECT, capture_output=True, text=True, timeout=15)
    second = subprocess.run(command, cwd=PROJECT, capture_output=True, text=True, timeout=15)
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["stages"]["s1"]
    attempts = sorted(p.name for p in (run / "stages" / "s1").iterdir() if p.is_dir())
    return {"check": "retry_same_config", "first_exit_code": first.returncode,
            "second_exit_code": second.returncode, "invocations": int(counter.read_text()),
            "final_status": record["status"], "attempts": attempts,
            "confirmed": first.returncode != 0 and second.returncode == 0
                         and int(counter.read_text()) == 2 and record["status"] == "success"
                         and attempts == ["attempt-001", "attempt-002"],
            "meaning": "A transient subprocess failure is retried as a new attempt with the unchanged config and succeeds."}


def check_complete_without_report(root: Path) -> dict:
    case = root / "complete_without_report"
    fakebin = case / "fakebin"
    fakebin.mkdir(parents=True)
    fake = fakebin / "codex"
    fake.write_text("""#!/usr/bin/env python3
import json, pathlib, re, sys
if '--version' in sys.argv:
    print('fake-codex 0')
    raise SystemExit(0)
args = sys.argv
pathlib.Path(args[args.index('--output-last-message') + 1]).write_text('finished\\n')
prompt = sys.stdin.read()
result_path = re.search(r'Before finishing, write valid JSON to this path:\\n([^\\n]+)', prompt).group(1)
result = {'summary': 'completed without report', 'artifacts': [__ARTIFACT__], 'evidence': [], 'claims': [],
          'limitations': [], 'next_actions': [], 'decision': 'complete',
          'research_status': 'done', 'candidate': None}
pathlib.Path(result_path).write_text(json.dumps(result))
""".replace("__ARTIFACT__", json.dumps(EXISTING_PROJECT_FILE)), encoding="utf-8")
    fake.chmod(0o755)
    brief = case / "brief.md"
    brief.write_text("fake brief\n", encoding="utf-8")
    run = case / "run"
    env = dict(os.environ)
    env["PATH"] = str(fakebin) + os.pathsep + env.get("PATH", "")
    proc = subprocess.run([sys.executable, str(PROJECT / "src/discover.py"), "--brief", str(brief),
                           "--run-dir", str(run), "--max-actions", "1"],
                          cwd=PROJECT, env=env, capture_output=True, text=True, timeout=20)
    state = json.loads((run / "discovery_state.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    report_path = Path(manifest["stages"]["c00_coordinator"]["output_path"]) / "REPORT.md"
    initial_report_exists = report_path.exists()
    original_result = Path(state["decisions"][0]["result_path"])
    original_hash = runtime.sha256_file(original_result)
    repeated = subprocess.run([sys.executable, str(PROJECT / "src/discover.py"), "--brief", str(brief),
                               "--run-dir", str(run), "--max-actions", "1"],
                              cwd=PROJECT, env=env, capture_output=True, text=True, timeout=20)
    state_after_repeat = json.loads((run / "discovery_state.json").read_text(encoding="utf-8"))
    stages_after_repeat = json.loads((run / "manifest.json").read_text(encoding="utf-8"))["stages"]
    report_path.write_text("Explicit manual repair record for the fake test.\n", encoding="utf-8")
    repaired = subprocess.run([sys.executable, str(PROJECT / "src/discover.py"), "--brief", str(brief),
                               "--run-dir", str(run), "--max-actions", "1"],
                              cwd=PROJECT, env=env, capture_output=True, text=True, timeout=20)
    final_state = json.loads((run / "discovery_state.json").read_text(encoding="utf-8"))
    return {"check": "complete_without_report", "discover_exit_code": proc.returncode,
            "state_status": state["status"], "report_exists_initially": initial_report_exists,
            "error": proc.stderr.splitlines()[-1] if proc.stderr else "",
            "same_config_retry_exit_code": repeated.returncode,
            "state_after_retry": state_after_repeat["status"],
            "coordinator_stages_after_retry": len(stages_after_repeat),
            "manual_report_repair_exit_code": repaired.returncode,
            "state_after_manual_report_repair": final_state["status"],
            "coordinator_result_unchanged": runtime.sha256_file(original_result) == original_hash,
            "confirmed": proc.returncode != 0 and state["status"] == "running"
                         and repeated.returncode != 0 and state_after_repeat["status"] == "running"
                         and len(stages_after_repeat) == 1 and repaired.returncode == 0
                         and final_state["status"] == "complete"
                         and runtime.sha256_file(original_result) == original_hash,
            "meaning": "Missing report stays incomplete on same-config resume; adding the missing report explicitly recovers without altering coordinator result.json."}


def main() -> None:
    review_dir = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="fake-check-", dir=review_dir) as temporary:
        root = Path(temporary)
        results = [check_dependency_fingerprint(), check_shape_only_success(root),
                   check_timeout_kills_process_group(root), check_invalid_dispatch_resume(root),
                   check_retry_same_config(root), check_complete_without_report(root)]
    output = review_dir / "fake_check_results_v2.json"
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
