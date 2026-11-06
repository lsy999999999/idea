"""Evidence-driven dispatcher. Scientific next steps are chosen by Luna, not this script."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

PROJECT = Path(__file__).resolve().parents[1]
ROLES = {
    "boundary": "Find a concrete explanatory gap in accessible observations. Inspect actual data and existing explanations. Consider noise, measurement and parameter errors before proposing a new construct.",
    "bridge": "Retrieve relevant literature and cross-domain concepts for a specific gap. Explain the mapping and its conditions. Save actual sources and identify closest prior work; do not invent citations or claim world novelty from a short search.",
    "theorist": "Turn evidence into a small set of competing, operational hypotheses. Define any new state/relationship/variable and the distinctive predictions. You can change the question or reject the premise.",
    "experimentalist": "Write and execute reproducible analyses or computational experiments addressing the most informative unresolved question. Save predictions before new tests, use appropriate controls, record failures and actual results. Do not replace science with only forecast fitting.",
    "skeptic": "Independently inspect scientific claims, the data and executed code. Check leakage, units, confounding, uncertainty, prior work and competing explanations. Recompute important quantities; give an actionable scientific next step.",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def inside(path):
    path = Path(path).resolve()
    if not path.is_relative_to(PROJECT):
        raise ValueError(f"Path must be in project: {path}")
    return path


def stage_run(run, stage_id, role, prompt, inputs, model, effort, timeout):
    config = {
        "model": model,
        "reasoning_effort": effort,
        "network_access": True,
        "run_dir": str(run),
        "stages": [{"id": stage_id, "role": role, "prompt": prompt,
                    "inputs": [str(p) for p in inputs], "timeout_s": timeout}],
    }
    path = run / "dispatch" / f"{stage_id}.json"
    if path.exists() and read(path) != config:
        raise RuntimeError(f"Existing dispatch changed: {path}")
    write(path, config)
    def normalize_summary_object():
        manifest_path = run / "manifest.json"
        if role == "coordinator" or not manifest_path.is_file():
            return None
        record = read(manifest_path).get("stages", {}).get(stage_id, {})
        if (record.get("status") != "incomplete" or record.get("returncode") != 0
                or record.get("result_error") != "summary must be a nonempty string"):
            return None
        workspace = inside(record["output_path"])
        source = workspace / "result.json"
        raw = read(source)
        summary = raw.get("summary")
        if not isinstance(summary, dict) or not isinstance(summary.get("text"), str) or not summary["text"].strip():
            return None
        if any(not isinstance(raw.get(k), list) for k in ("artifacts", "evidence", "claims", "limitations", "next_actions")):
            return None
        if not raw["artifacts"]:
            return None
        for artifact in raw["artifacts"]:
            locator = artifact.get("path") if isinstance(artifact, dict) else artifact
            if not isinstance(locator, str):
                return None
            apath = Path(locator)
            candidates = [apath] if apath.is_absolute() else [workspace / apath, PROJECT / apath]
            if not any(p.resolve().is_relative_to(PROJECT) and p.exists() for p in candidates):
                return None
        recovered = dict(raw)
        recovered["summary"] = summary["text"]
        recovered["agent_supplied_summary_metadata"] = summary
        recovered["format_recovery"] = {"source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "rule": "Use summary.text verbatim; preserve the original summary object and all other fields.",
            "scientific_values_changed": False}
        recovered_path = run / "dispatch" / f"{stage_id}_attempt_{record['attempt']}_normalized.json"
        if not recovered_path.exists():
            write(recovered_path, recovered)
        return recovered_path, read(recovered_path)
    def timed_out_research_result():
        manifest_path = run / "manifest.json"
        if role == "coordinator" or not manifest_path.is_file():
            return None
        record = read(manifest_path).get("stages", {}).get(stage_id, {})
        if record.get("status") != "failed" or not record.get("timed_out"):
            return None
        result_path = run / "dispatch" / f"{stage_id}_attempt_{record['attempt']}_timeout.json"
        result = {
            "summary": f"Role {role} reached its execution time limit. This is an operational failure, not a scientific result. Partial files are retained for a narrower follow-up.",
            "artifacts": [{"path": record["output_path"], "description": "Unreviewed partial workspace; do not assume completion"}],
            "evidence": [{"type": "execution_record", "source": str(manifest_path), "stage": stage_id,
                          "attempt": record["attempt"], "elapsed_s": record["elapsed_s"]}],
            "claims": [],
            "limitations": ["The research role did not finish; any partial scientific output requires inspection."],
            "next_actions": ["Choose a smaller substantive action, reuse inspectable saved data, or pivot. Do not blindly repeat the entire timed-out task."],
            "execution_status": "timed_out",
        }
        if not result_path.exists():
            write(result_path, result)
        return result_path, read(result_path)
    recovered = normalize_summary_object() or timed_out_research_result()
    if recovered:
        return recovered
    print(json.dumps({"time": now(), "event": "dispatch", "stage": stage_id, "role": role}), flush=True)
    completed = subprocess.run([sys.executable, str(PROJECT / "src/runtime.py"), "--config", str(path)], cwd=PROJECT)
    if completed.returncode:
        recovered = normalize_summary_object() or timed_out_research_result()
        if recovered:
            return recovered
        raise RuntimeError(f"Stage {stage_id} failed; inspect its runtime manifest and resume.")
    manifest = read(run / "manifest.json")
    item = manifest["stages"][stage_id]
    if item["status"] != "success":
        raise RuntimeError(f"Stage {stage_id} is not successful: {item['status']}")
    result_path = inside(item["result_path"])
    return result_path, read(result_path)


def coordinator_prompt(run, state, max_actions):
    remaining = max_actions - len(state["actions"])
    return f"""You are the scientific coordinator of an exploratory discovery team.
The user's priority is a real useful new idea with preliminary evidence. Do not start by building a benchmark.
Start in exploration mode: use an available valid subset for a small substantive calculation
after initial source checks. Unknown metadata limits scope; only a concrete data error blocks
all analysis. Do not spend consecutive actions on comprehensive coverage or provenance audits.
A familiar feature improving a forecast is a lead, not the final discovery objective. Ask
which explanatory distinction the observations require, formulate competing predictions,
and spend the next action on evidence that can change that judgment. Reuse completed reviews
instead of repeatedly auditing already checked numbers. Save negative results and revise.
Read the brief and evidence index provided as input files. Read underlying research artifacts as needed.
Read the latest action result in full before deciding. The evidence index lists outcomes
newest first. Older coordinator summaries are historical opinions, not the current state.
For a final report, open every action result referenced by the index and include a compact
coverage table. Distinguish an execution timeout from scientific files later completed or
independently verified. State which hypotheses were supported, contradicted, or untested.
    Choose the next question/action from the actual evidence. Preserve disagreement and failed hypotheses.
Do not import old projects or invent a target formula. Do not perform the experiment yourself: dispatch it.
Available roles: {json.dumps(ROLES, ensure_ascii=False)}
Run directory: {run}
Remaining research actions: {remaining}. Spend them on useful evidence, not ritual role completion.
Use public literature/data and local executable experiments. Natural observations and software/simulation studies
are both possible, but clearly state their scientific scope. Prefer accessible real measurements when feasible.
If results are negative, revise the hypothesis or change the question rather than merely weaken acceptance criteria.
Before calling a candidate supported, obtain a distinct prediction tested against genuinely new observations or
an independent computational intervention, and inspect the strongest alternative explanations.
An initial promising candidate with unresolved novelty is a valid preliminary outcome; say exactly what remains.

Write result.json with the runtime's six required fields. Also add:
"decision": "dispatch" | "complete" | "blocked",
"research_status": a concise honest description,
"candidate": an object containing current problem, idea, evidence status and unresolved question (or null).
For dispatch, next_actions MUST contain exactly one object:
{{"role":"one of boundary/bridge/theorist/experimentalist/skeptic", "task":"specific useful task with expected artifacts",
  "inputs":["absolute paths to existing files inside the project"]}}.
Choose complete only when there is a reviewable preliminary result, or after useful actions are exhausted.
Choose blocked only for a concrete missing resource. On complete/blocked use next_actions=[] and write a Chinese
REPORT.md in your workspace, covering what actually ran, the candidate, evidence, failed ideas and next test.
If remaining actions is zero you MUST finalize honestly; never claim success merely because the budget ended.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--brief", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--max-actions", type=int, default=7)
    ap.add_argument("--model", default="gpt-6-luna")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()
    if not 1 <= args.max_actions <= 30:
        raise ValueError("max-actions must be 1..30")
    run = inside(args.run_dir)
    brief = inside(args.brief)
    run.mkdir(parents=True, exist_ok=True)
    state_path = run / "discovery_state.json"
    settings = {"brief": str(brief), "brief_sha256": hashlib.sha256(brief.read_bytes()).hexdigest(),
                "model": args.model, "effort": args.effort, "max_actions": args.max_actions}
    if state_path.exists():
        state = read(state_path)
        if state["settings"] != settings:
            raise RuntimeError("Resume settings differ; start a new run or use original settings")
        if state["status"] in ("complete", "blocked"):
            print(json.dumps(state, ensure_ascii=False)); return
    else:
        state = {"created_at": now(), "settings": settings, "status": "running", "actions": [], "decisions": []}
        write(state_path, state)
    while True:
        index = len(state["actions"])
        # Stable evidence snapshots make resume hashing independent of subsequent state changes.
        evidence_path = run / "dispatch" / f"evidence_{index:02d}.json"
        evidence = {
            "brief": str(brief),
            "actions_newest_first": [{"role": a["role"], "result_path": a["result_path"],
                "summary": a["result"].get("summary"),
                "execution_status": a["result"].get("execution_status", "result_available")}
                for a in reversed(state["actions"])],
            "latest_decision": state["decisions"][-1] if state["decisions"] else None,
            "older_decision_paths": [d["result_path"] for d in state["decisions"][:-1]],
        }
        if not evidence_path.exists():
            write(evidence_path, evidence)
        if len(state["decisions"]) <= index:
            coordinator_inputs = [brief, evidence_path]
            if state["actions"]:
                coordinator_inputs.insert(0, Path(state["actions"][-1]["result_path"]))
            result_path, result = stage_run(run, f"c{index:02d}_coordinator", "coordinator",
                coordinator_prompt(run, state, args.max_actions), coordinator_inputs, args.model, args.effort, args.timeout)
            decision = result.get("decision")
            if decision not in ("dispatch", "complete", "blocked"):
                raise ValueError("Coordinator omitted a valid decision; review artifact before resume")
            state["decisions"].append({"result_path": str(result_path), "result": result})
            write(state_path, state)
        else:
            result_path = Path(state["decisions"][index]["result_path"])
            result = state["decisions"][index]["result"]
            decision = result["decision"]
        if decision != "dispatch":
            report = result_path.parent / "REPORT.md"
            if not report.is_file() or not report.read_text().strip():
                raise RuntimeError("Coordinator finalized without a nonempty REPORT.md; review before completing run")
            state.update(status=decision, finished_at=now(), final_result_path=str(result_path))
            write(state_path, state)
            print(json.dumps({"event": "finished", "status": decision, "research_actions": index,
                              "result_path": str(result_path)}, ensure_ascii=False), flush=True)
            return
        if index >= args.max_actions:
            raise RuntimeError("Coordinator exceeded scientific action budget; result retained")
        actions = result.get("next_actions", [])
        if len(actions) != 1 or not isinstance(actions[0], dict):
            raise ValueError("Coordinator must dispatch exactly one structured action")
        action = actions[0]
        role = action["role"]
        if role not in ROLES:
            raise ValueError(f"Unknown role {role}")
        inputs = [brief, evidence_path, result_path]
        for p in action.get("inputs", []):
            p = inside(p)
            if not p.is_file():
                raise FileNotFoundError(p)
            if p not in inputs:
                inputs.append(p)
        prompt = (f"You are the {role} research agent. {ROLES[role]}\n"
                  f"Scientific assignment:\n{action['task']}\n"
                  f"Shared run directory: {run}\nUse {PROJECT / '.venv/bin/python'} for numerical work.\n"
                  "Execute the assigned work now, save code/data/evidence, and report actual outcomes in result.json. "
                  "Give the next informative step; do not dispatch more agents yourself. "
                  "Save your new artifacts in your assigned workspace. Reference earlier evidence by absolute path.")
        rpath, reply = stage_run(run, f"r{index:02d}_{role}", role, prompt, inputs, args.model, args.effort, args.timeout)
        state["actions"].append({"role": role, "task": action["task"], "result_path": str(rpath), "result": reply})
        write(state_path, state)


if __name__ == "__main__":
    main()
