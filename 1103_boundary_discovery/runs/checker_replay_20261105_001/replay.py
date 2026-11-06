"""Audited replay adapter; unchanged current checker, one historical idea per call."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from discover import read, stage_run, write
from idea_check import CHECKER_PROMPT, POLICY, SCHEMA_VERSION, validate_checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=int, required=True)
    args = parser.parse_args()
    plan = read(ROOT / "PLAN.json")
    case = plan["cases"][args.case - 1]
    run = ROOT / "cases" / case["case"]
    run.mkdir(parents=True, exist_ok=True)
    idea_path = run / "ideas.json"
    if not idea_path.exists():
        shutil.copy2(case["input"], idea_path)
        shutil.copy2(ROOT / "OPERATOR_STEERING.md", run / "OPERATOR_STEERING.md")
    packet = read(idea_path)
    assert hashlib.sha256(json.dumps(packet["ideas"][0], ensure_ascii=False, sort_keys=True).encode()).hexdigest() == case["idea_sha256"]
    try:
        path, result = stage_run(run, "check", "idea_check_agent", CHECKER_PROMPT,
            [idea_path, POLICY], plan["model"], plan["effort"], plan["timeout_s_per_idea"])
        checks = validate_checks(result, packet["ideas"], require_claims=True)
        write(run / "check_report.json", {"schema_version": SCHEMA_VERSION,
            "ideas_path": str(idea_path), "check_result_path": str(path),
            "checks": checks, "searches": result["searches"]})
        write(run / "STATUS.json", {"status": "complete", "result": str(path)})
        print(json.dumps({"case": case["case"], "status": "complete",
            "prior": checks[0]["prior_work"]["verdict"],
            "coverage": checks[0]["novelty"]["overall_status"]}), flush=True)
    except Exception as exc:
        write(run / "STATUS.json", {"status": "failed", "error": str(exc)})
        raise


if __name__ == "__main__":
    main()
