#!/usr/bin/env python3
"""Same-config recovery checks using only a deterministic fake Codex CLI."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


PROJECT = Path(__file__).resolve().parents[2]
REVIEW = Path(__file__).resolve().parent


def scenario(root: Path, name: str) -> dict:
    case = root / name
    fake_bin = case / "bin"
    fake_bin.mkdir(parents=True)
    count_file = case / "calls.txt"
    fake = fake_bin / "codex"
    fake.write_text("""#!/usr/bin/env python3
import json, pathlib, re, sys
if '--version' in sys.argv:
    print('fake-codex regression')
    raise SystemExit(0)
scenario = __SCENARIO__
count_file = pathlib.Path(__COUNT_FILE__)
count = int(count_file.read_text()) + 1 if count_file.exists() else 1
count_file.write_text(str(count))
args = sys.argv
pathlib.Path(args[args.index('--output-last-message') + 1]).write_text('fake response\\n')
prompt = sys.stdin.read()
result_path = pathlib.Path(re.search(r'Before finishing, write valid JSON to this path:\\n([^\\n]+)', prompt).group(1))
if count == 1 and scenario == 'bad_dispatch_then_complete':
    decision = 'dispatch'
    next_actions = [{}]
    write_report = False
elif count == 1 and scenario == 'missing_report_then_complete':
    decision = 'complete'
    next_actions = []
    write_report = False
else:
    decision = 'complete'
    next_actions = []
    write_report = True
result = {
    'summary': 'fake coordinator attempt ' + str(count),
    'artifacts': ['result.json'],
    'evidence': [], 'claims': [], 'limitations': [],
    'next_actions': next_actions,
    'decision': decision,
    'research_status': 'fake regression only',
    'candidate': None,
}
result_path.write_text(json.dumps(result), encoding='utf-8')
if write_report:
    result_path.with_name('REPORT.md').write_text('Fake reviewable report.\\n', encoding='utf-8')
""".replace("__SCENARIO__", json.dumps(name)).replace(
        "__COUNT_FILE__", repr(str(count_file))), encoding="utf-8")
    fake.chmod(0o755)
    brief = case / "brief.md"
    brief.write_text("Controlled fake regression; no research content.\n", encoding="utf-8")
    run_dir = case / "run"
    env = dict(os.environ)
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
    command = [sys.executable, str(PROJECT / "src/discover.py"), "--brief", str(brief),
               "--run-dir", str(run_dir), "--max-actions", "1", "--timeout", "15"]

    first = subprocess.run(command, cwd=PROJECT, env=env, capture_output=True, text=True, timeout=25)
    first_state = json.loads((run_dir / "discovery_state.json").read_text(encoding="utf-8"))
    manifest_after_first = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    first_record = manifest_after_first["stages"]["c00_coordinator"]
    first_completion = json.loads((run_dir / "stages/c00_coordinator/attempt-001/completion.json").read_text(encoding="utf-8"))

    second = subprocess.run(command, cwd=PROJECT, env=env, capture_output=True, text=True, timeout=25)
    final_state = json.loads((run_dir / "discovery_state.json").read_text(encoding="utf-8"))
    final_manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    final_record = final_manifest["stages"]["c00_coordinator"]
    second_completion_path = run_dir / "stages/c00_coordinator/attempt-002/completion.json"
    second_completion = json.loads(second_completion_path.read_text(encoding="utf-8"))
    valid_result = json.loads(Path(final_record["result_path"]).read_text(encoding="utf-8"))
    report_path = Path(final_record["result_path"]).with_name("REPORT.md")
    passed = (
        first.returncode != 0
        and first_state["status"] == "running"
        and first_state["decisions"] == []
        and first_completion["status"] == "incomplete"
        and second.returncode == 0
        and final_state["status"] == "complete"
        and len(final_state["decisions"]) == 1
        and final_state["decisions"][0]["result"]["decision"] == "complete"
        and final_record["attempt"] == 2
        and second_completion["status"] == "success"
        and valid_result["decision"] == "complete"
        and report_path.is_file() and report_path.read_text(encoding="utf-8").strip()
        and int(count_file.read_text()) == 2
    )
    return {
        "scenario": name,
        "first_exit_code": first.returncode,
        "first_runtime_status": first_completion["status"],
        "decisions_cached_after_first_attempt": len(first_state["decisions"]),
        "second_exit_code": second.returncode,
        "attempts_preserved": [first_completion["attempt"], second_completion["attempt"]],
        "attempt_statuses": [first_completion["status"], second_completion["status"]],
        "final_state": final_state["status"],
        "final_decision": valid_result["decision"],
        "report_present": report_path.is_file(),
        "fake_cli_invocations": int(count_file.read_text()),
        "confirmed": passed,
        "errors": {
            "first_stderr_tail": first.stderr.splitlines()[-1] if first.stderr else "",
            "second_stderr_tail": second.stderr.splitlines()[-1] if second.stderr else "",
        },
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="final-regression-", dir=REVIEW) as temp:
        root = Path(temp)
        results = [scenario(root, "bad_dispatch_then_complete"),
                   scenario(root, "missing_report_then_complete")]
    output = {
        "scope": "Offline fake-CLI regression only; no model calls and no pilot access.",
        "results": results,
        "all_confirmed": all(item["confirmed"] for item in results),
    }
    (REVIEW / "FINAL_REGRESSION.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
