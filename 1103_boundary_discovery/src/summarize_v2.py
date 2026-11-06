"""Summarize execution and evidence transitions without rating scientific novelty."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


def summarize(run):
    run = Path(run).resolve()
    state = json.loads((run / "v2_state.json").read_text())
    manifest = json.loads((run / "manifest.json").read_text())
    records = [json.loads(p.read_text()) for p in sorted(run.glob("stages/*/attempt-*/completion.json"))]
    ledger = state["ledger"]
    evidence = ledger["evidence"]
    plans_compared = 0
    for item in state["rounds"]:
        planner = json.loads(Path(item["planner_result"]).read_text())
        plans_compared += len(planner.get("plans", []))
    stage_groups = {}
    for stage, record in manifest["stages"].items():
        group = stage.split("_")[0]
        totals = stage_groups.setdefault(group, {"latest_attempts": 0, "elapsed_seconds": 0})
        totals["latest_attempts"] += 1
        totals["elapsed_seconds"] += record["elapsed_s"]
    return {
        "run": str(run), "status": state["status"], "requested_model": state["settings"]["model"],
        "fork_provenance": state.get("fork_provenance"),
        "model_calls_completed": len(records),
        "runtime_status_counts": dict(Counter(x["status"] for x in records)),
        "model_stage_wall_seconds_sum": round(sum(x["elapsed_s"] for x in records), 3),
        "latest_stage_groups": stage_groups,
        "initial_independent_contexts": len(state["seeds"]),
        "hypothesis_count": len(ledger["hypotheses"]),
        "hypothesis_status_counts": dict(Counter(h["status"] for h in ledger["hypotheses"].values())),
        "hypothesis_lineage": {hid: h.get("parent_id") for hid, h in ledger["hypotheses"].items()},
        "proposed_experiment_plans_in_executed_rounds": plans_compared,
        "executed_experiment_count": len(state["rounds"]),
        "experiment_execution_status_counts": dict(Counter(e["execution_status"] for e in evidence)),
        "observed_classifications": [{"experiment_id": e["experiment_id"],
            "outcome": e["observed_outcome_id"], "relations": e["relations"]} for e in evidence],
        "review_flags": {hid: h.get("review_flags", []) for hid, h in ledger["hypotheses"].items()
                         if h.get("review_flags")},
        "final_report": state.get("final_report"),
        "interpretation": "Execution and state-transition counts only. They do not establish scientific novelty, causality, or superiority to V1/single agent. Model-stage wall time includes reasoning, tools and wait time; it is not pure inference cost.",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir")
    p.add_argument("--output")
    args = p.parse_args()
    text = json.dumps(summarize(args.run_dir), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text)
    print(text, end="")
