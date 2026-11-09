"""Read-only audit of actual learning outputs and cross-task memory provenance."""
import argparse
import json
from pathlib import Path

from discover import PROJECT, read, write
from learning_memory import digest
from runtime import sha256_tree
from idea_check import validate_checks, validate_ideas


def audit(run):
    state = read(run / "learning_state.json")
    manifest = read(run / "manifest.json")
    checks = []
    stages = []
    for sid, saved in state["stages"].items():
        path = Path(saved["path"])
        result = read(path)
        record = next(v for v in manifest["stages"].values() if v.get("result_path") == str(path))
        checks.append({"check": sid + " result hash", "pass": digest(path) == saved["sha256"]})
        checks.append({"check": sid + " workspace hash", "pass": sha256_tree(Path(record["output_path"])) == record["output_sha256"]})
        stages.append({"id": sid, "requested_model": record["requested_model"],
                       "elapsed_s": record["elapsed_s"], "summary": result["summary"],
                       "memory_use": result.get("memory_use", []),
                       "question_before": result.get("question_before", result.get("initial_question")),
                       "question_after": result.get("question_after"),
                       "learning_request": result.get("learning_request"),
                       "learning_change": result.get("learning_change"),
                       "path": str(path)})
    retrievals = []
    for path in sorted((run / "memory_retrieval").glob("*.json")):
        packet = read(path)
        notes = [{"key": item["note"]["key"], "version": item["note"]["version"],
                  "source_task": item["note"]["source_task"], "kind": item["note"]["kind"]}
                 for item in packet["retrieved"]]
        retrievals.append({"path": str(path), "researcher": packet["researcher"], "notes": notes})
        for item in packet["retrieved"]:
            note = item["note"]
            checks.append({"check": path.name + " provenance " + note["key"],
                           "pass": digest(note["source_result"]) == note["source_sha256"]})
    candidates = read(run / "ideas.json") if (run / "ideas.json").exists() else {"ideas": []}
    report = read(run / "check_report.json") if (run / "check_report.json").exists() else {}
    if candidates["ideas"]:
        validate_checks(report, validate_ideas(candidates))
    return {"run": str(run), "status": state["status"], "checks_passed": all(x["pass"] for x in checks),
            "integrity_checks": checks, "stages": stages, "retrievals": retrievals,
            "ideas": candidates["ideas"], "idea_checks": report.get("checks", [])}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--prefix", default="learn_20261104")
    args = p.parse_args()
    output = {"cases": [audit(path) for path in sorted((PROJECT / "runs").glob(args.prefix + "_*"))]}
    path = PROJECT / "learning_lab" / "AUDIT.json"
    write(path, output)
    print(json.dumps({"output": str(path), "all_pass": all(c["checks_passed"] for c in output["cases"]),
                      "cases": [{"run": c["run"], "status": c["status"], "stages": len(c["stages"])} for c in output["cases"]]}))
