"""Competing explanations, frozen discriminating plans, and evidence-derived state.

Scientific choices are model outputs. Structural validation and state propagation
are deterministic; neither constitutes scientific or novelty validation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil

from discover import PROJECT, inside, now, read, stage_run, write
from hypothesis_ledger import empty_ledger, apply_proposals, validate_experiment, apply_observations

CONTRACT = PROJECT / "docs/V2_CONTRACT.md"


def freeze(path, value):
    path = Path(path)
    if path.exists():
        if read(path) != value:
            raise ValueError(f"Frozen artifact changed: {path}")
    else:
        write(path, value)
    return path


def check_artifacts(observation, workspace):
    paths = observation.get("artifacts", [])
    if observation.get("execution_status") == "completed" and not paths:
        raise ValueError("Completed experiment must identify actual saved artifacts")
    for item in paths:
        raw = item.get("path") if isinstance(item, dict) else item
        if not isinstance(raw, str):
            raise ValueError("Observation artifact must be a path")
        path = Path(raw)
        choices = [path] if path.is_absolute() else [workspace / path, PROJECT / path]
        if not any(p.resolve().is_relative_to(PROJECT) and p.exists() for p in choices):
            raise ValueError(f"Missing observation artifact: {raw}")


def add_review(ledger, findings, source):
    """Mark questionable classifications; never silently relabel observations."""
    updated = copy.deepcopy(ledger)
    if not isinstance(source, str) or not source.strip():
        raise ValueError("review source must be a nonempty string")
    if not isinstance(findings, list):
        raise ValueError("review_findings must be an array")
    seen = set()
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("each review finding must be an object")
        eid = finding.get("experiment_id")
        if eid not in updated["experiments"]:
            raise ValueError(f"Unknown reviewed experiment {eid}")
        if eid in seen:
            raise ValueError(f"Duplicate review finding for {eid}")
        seen.add(eid)
        valid = finding.get("classification_valid")
        if valid is not None and not isinstance(valid, bool):
            raise ValueError("classification_valid must be boolean or null")
        if not isinstance(finding.get("reason"), str) or not finding["reason"].strip():
            raise ValueError("review requires a reason")
        if not isinstance(finding.get("evidence_paths", []), list):
            raise ValueError("review evidence_paths must be an array")
        if valid is not True:
            # Flag only hypotheses whose predeclared effects used this experiment.
            affected = {hid for item in updated["evidence"] if item.get("experiment_id") == eid
                        for hid in item.get("relations", {})}
            if not affected:
                raise ValueError(f"No hypothesis evidence recorded for reviewed experiment {eid}")
            queue = list(affected)
            while queue:
                dependency = queue.pop(0)
                for hid, hypothesis in updated["hypotheses"].items():
                    if dependency in hypothesis.get("depends_on", []) and hid not in affected:
                        affected.add(hid)
                        queue.append(hid)
            for hid in affected:
                h = updated["hypotheses"][hid]
                h.setdefault("review_flags", []).append({"experiment_id": eid, "source": source,
                    "reason": finding["reason"], "classification_valid": valid})
                h["review_status"] = "needs_review"
    updated["review"] = {"source": source, "findings": copy.deepcopy(findings)}
    return updated


def planner_prompt(remaining, timeout):
    return f"""You coordinate a V2 discovery run. Read the current ledger first, then actual
prior experiment results. Never substitute an older prose summary for ledger evidence.
Read V2_CONTRACT.md for exact additional output fields.
Research experiment slots remaining: {remaining}. Each experiment has at most {timeout} seconds.
Choose the next experiment by what it can distinguish, feasibility, and cost. Propose two
different feasible plans and select one; no fictitious precision or numerical utility scores.
Use cheap interventions on the real system in the brief. Do not spend a slot merely repeating
source/coverage checks. Different wording is not a different scientific prediction.
You may add new hypothesis proposals or revised representations with new IDs and parent_id.
This is how the system escapes an inadequate starting vocabulary; it is not limited to the
initial proposals. Known effects are useful baselines, not new discoveries. Prefer a concrete
boundary, relation, or failure condition not settled by the nearby literature. Retrieve public
sources as needed, but do not run the chosen experiment in this planning stage.
Plans must include measurable mutually exclusive outcome classes and an inconclusive class;
write classification rules and replicate/seed rules before the experiment executes.
At least two hypotheses must predict different observable classes. If they are compatible,
revise or add a useful alternative instead of inventing a false opposition. Modifying only
a parameter or an already known explanatory variable may be useful but does not establish novelty.
Keep the strongest simple known explanation. Do not protect a candidate from negative results.
Use unused seeds/regimes or a changed intervention when testing a new prediction; declare any
reuse exploratory. Select replication only when it tests a specific remaining uncertainty.
If no affordable action can distinguish hypotheses, finalize honestly and identify the needed
measurement. With zero remaining slots you MUST finalize (plans=[], selected_plan_id=null).
Output decision, proposals, plans, selected_plan_id, selection_reason in result.json in addition
to runtime fields. Do not write a final manuscript here; a final independent check follows.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--max-experiments", type=int, default=3)
    parser.add_argument("--model", default="gpt-6-luna")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    if not 1 <= args.max_experiments <= 10:
        raise ValueError("max-experiments must be 1..10")
    brief, run = inside(args.brief), inside(args.run_dir)
    run.mkdir(parents=True, exist_ok=True)
    state_file = run / "v2_state.json"
    settings = {"brief": str(brief), "brief_sha256": hashlib.sha256(brief.read_bytes()).hexdigest(),
        "model": args.model, "effort": args.effort, "max_experiments": args.max_experiments,
        "timeout": args.timeout}
    if state_file.exists():
        state = read(state_file)
        if state["settings"] != settings:
            raise ValueError("Resume settings changed")
        if state["status"] == "complete":
            print(json.dumps({"status": "complete", "report": state["final_report"]})); return
    else:
        state = {"created_at": now(), "settings": settings, "status": "running",
            "ledger": empty_ledger(), "seeds": [], "bridge": None, "rounds": [], "review": None}
        snapshot = run / "controller_source"
        snapshot.mkdir(exist_ok=True)
        for name in ("discover_v2.py", "hypothesis_ledger.py", "discover.py", "runtime.py"):
            shutil.copy2(PROJECT / "src" / name, snapshot / name)
        shutil.copy2(CONTRACT, snapshot / CONTRACT.name)
        write(state_file, state)

    def call(stage, role, task, inputs):
        return stage_run(run, stage, role, task, [brief, CONTRACT, *inputs],
                         args.model, args.effort, args.timeout)

    # Separate initial contexts: prompt-level independence, not enforced read isolation.
    for index, prefix in enumerate(("A", "B")):
        if len(state["seeds"]) > index:
            continue
        lens = (
            "Focus on mechanistic explanation, operational measurement, and the smallest predictive state that could explain the observed boundary."
            if prefix == "A" else
            "Focus on the strongest simple known baseline, counterexamples in observability, and conditions that would defeat an apparent novel relation."
        )
        task = f"""Independently propose 1-2 concrete explanations for the real phenomenon in
the brief, using IDs {prefix}1/{prefix}2. Read only the brief, its cited scout data/code, and
public sources; DO NOT inspect another seed proposal or other runs. This is prompt-level
independent ideation, not statistical independence. Study known explanations and look for
where the current representation collapses distinguishable cases. Give an operational
measurement, a falsifiable conditional prediction, and the strongest alternative.
{lens}
Retrieve closest prior work with actual sources. Do not perform a large experiment or
construct an invented world with a planted answer. Prioritize a small useful candidate over
a comprehensive review. Save result.json with proposals using V2_CONTRACT.md, plus the
runtime fields. All scientific claims begin untested; do not call an old concept new.
"""
        path, result = call(f"seed_{prefix}", "v2_independent_proposer", task, [])
        proposals = result.get("proposals")
        if not isinstance(proposals, list) or not proposals:
            raise ValueError("Independent proposer produced no proposals")
        state["ledger"] = apply_proposals(state["ledger"], proposals, str(path))
        state["seeds"].append(str(path))
        write(state_file, state)

    if not state["bridge"]:
        ledger_path = freeze(run / "snapshots/initial_ledger.json", state["ledger"])
        path, result = call("bridge", "v2_cross_domain_researcher", """Compare the independently
proposed explanations. Retrieve a small number of actual closest-prior and cross-domain
sources for this specific gap. State which ideas are already known, which explanations are
compatible, and which measurable contrast could separate useful alternatives. If justified,
propose 0-2 new representations using IDs C1/C2 with explicit mapping, measurement, prior work,
and predictions under V2_CONTRACT.md. Do not invent a new variable solely to satisfy a form.
Do not run the planned scientific experiment. Output proposals (possibly empty), sources,
and a concise actionable synthesis in addition to runtime result fields.""", [ledger_path, *map(Path, state["seeds"])])
        state["ledger"] = apply_proposals(state["ledger"], result.get("proposals", []), str(path))
        state["bridge"] = str(path)
        write(state_file, state)

    while not state.get("planning_finished"):
        index = len(state["rounds"])
        ledger_path = freeze(run / f"snapshots/ledger_{index:02d}.json", state["ledger"])
        inputs = [ledger_path, Path(state["bridge"])]
        if state["rounds"]:
            inputs.append(Path(state["rounds"][-1]["result_path"]))
        path, result = call(f"plan_{index:02d}", "v2_planner",
                            planner_prompt(args.max_experiments - index, args.timeout), inputs)
        ledger = apply_proposals(state["ledger"], result.get("proposals", []), str(path))
        decision = result.get("decision")
        if decision == "finalize":
            if result.get("plans") != [] or result.get("selected_plan_id") is not None:
                raise ValueError("Finalization must not contain selected plans")
            state.update(ledger=ledger, planning_finished=True, final_planning_result=str(path))
            write(state_file, state)
            break
        if decision != "experiment" or index >= args.max_experiments:
            raise ValueError("Invalid planner decision or experiment budget exceeded")
        plans = result.get("plans")
        if not isinstance(plans, list) or len(plans) < 2:
            raise ValueError("Planner must compare at least two actions")
        if len({p["id"] for p in plans}) != len(plans):
            raise ValueError("Duplicate proposed plan IDs")
        for plan in plans:
            validate_experiment(ledger, plan)
        selected = [p for p in plans if p["id"] == result.get("selected_plan_id")]
        if len(selected) != 1 or not result.get("selection_reason"):
            raise ValueError("Planner must select one action with a reason")
        plan = selected[0]
        plan_path = freeze(run / f"frozen_plans/{index:02d}_{plan['id']}.json", plan)
        ledger_after_plan = freeze(run / f"snapshots/planned_ledger_{index:02d}.json", ledger)
        receipt_path = run / f"frozen_plans/{index:02d}_receipt.json"
        if not receipt_path.exists():
            write(receipt_path, {"frozen_at": now(), "plan_path": str(plan_path),
                "sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(), "planner_result": str(path)})
        experiment_path, experiment = call(f"experiment_{index:02d}", "v2_experimentalist", f"""Execute
ONLY the frozen experiment in {plan_path}. Read the plan before opening new outcome data.
Use {PROJECT / '.venv/bin/python'}. Use real system measurements, randomized order and independent
repeats as the plan specifies. Save executable code, raw per-trial results, classification
calculation, and a concise Chinese report. Keep the workload small enough to finish.
Do not change outcome classes or effect mappings. If classification is not justified, use
unclassified; if execution is incomplete, use partial/failed. A failed command is not a
scientific refutation. Report exact plan deviations. Do not propose hypothesis status updates.
Output observation per V2_CONTRACT.md in addition to runtime fields. Explicitly state which
outcome rule the actual numbers meet. Data from earlier experiments may guide engineering
setup, but no retrospective threshold choice or relabeling as held-out evidence.
""", [plan_path, ledger_after_plan, *([Path(state["rounds"][-1]["result_path"])] if state["rounds"] else [])])
        if hashlib.sha256(plan_path.read_bytes()).hexdigest() != read(receipt_path)["sha256"]:
            raise ValueError("Frozen plan was modified during execution")
        observation = experiment.get("observation")
        if observation is None and experiment.get("execution_status") == "timed_out":
            observation = {"experiment_id": plan["id"], "execution_status": "failed",
                "observed_outcome_id": "unclassified", "summary": "Runtime timed out; no scientific inference",
                "artifacts": [], "limitations": ["Partial artifacts require a new review"]}
        if not isinstance(observation, dict):
            raise ValueError("Experimentalist omitted observation")
        check_artifacts(observation, experiment_path.parent)
        ledger = apply_observations(ledger, plan, observation, str(experiment_path))
        state["ledger"] = ledger
        state["rounds"].append({"plan_path": str(plan_path), "planner_result": str(path),
            "result_path": str(experiment_path), "observation": observation})
        write(state_file, state)
        print(json.dumps({"event": "evidence_updated", "round": index,
                          "experiment": plan["id"], "outcome": observation["observed_outcome_id"]}), flush=True)

    final_ledger = freeze(run / "snapshots/ledger_before_review.json", state["ledger"])
    if not state["review"]:
        inputs = [final_ledger, *[Path(x[k]) for x in state["rounds"] for k in ("plan_path", "result_path")]]
        path, result = call("review", "v2_independent_reviewer", """Inspect every frozen plan and actual
result. Independently recompute at least one decisive metric from saved raw measurements, and
check that its classification follows the prewritten rule. Check intervention confounds,
independence/repeats, measurement and whether a supposedly new relation is already known.
This is a bounded final check, not a request for another general audit. Do not alter prior
artifacts. Save your own recomputation and source checks. Output review_findings under
V2_CONTRACT.md covering every executed experiment (classification_valid true/false/null), plus
runtime fields. Where unresolved, say exactly what invalidates or limits the conclusion.
""", inputs)
        findings = result.get("review_findings")
        expected_review_ids = {read(x["plan_path"])["id"] for x in state["rounds"]}
        if not isinstance(findings, list) or any(not isinstance(f, dict) for f in findings):
            raise ValueError("Review findings must be an array of objects")
        review_ids = [f.get("experiment_id") for f in findings]
        if len(review_ids) != len(set(review_ids)) or set(review_ids) != expected_review_ids:
            raise ValueError("Review must cover every executed experiment")
        state["ledger"] = add_review(state["ledger"], findings, str(path))
        state["review"] = str(path)
        write(state_file, state)
    final_ledger = freeze(run / "ledger.json", state["ledger"])
    final_inputs = [final_ledger, Path(state["review"]), Path(state["final_planning_result"]),
        *[Path(x["result_path"]) for x in state["rounds"]]]
    path, result = call("report", "v2_reporter", """Write REPORT.md in Chinese and result.json.
Read the authoritative current ledger and reviewer first, then each experiment result.
Cover ALL hypotheses and experiments in a compact evidence table, with existing sources.
Explain the original explanatory gap, representation changes, tested disagreements, actual
numbers, failed/untested predictions and the strongest remaining next question. Mark any
review_status=needs_review conclusion prominently; no unqualified support claim may depend on
it. Distinguish executed structural behavior, tentative scientific value and novelty status.
Do not claim superiority to V1/single agent: no controlled method comparison ran. Do not
call known effects new discoveries. If no novel supported relation emerged, say so directly.
Include source_coverage as objects {"kind":"hypothesis"|"experiment","id":"..."},
with exactly one entry per hypothesis ID and experiment ID. Prefer a
useful, precise next test over generic requests for more research. No new experiments here.
""", final_inputs)
    report = path.parent / "REPORT.md"
    if not report.is_file() or not report.read_text().strip():
        raise ValueError("Reporter omitted REPORT.md")
    coverage = result.get("source_coverage")
    if not isinstance(coverage, list):
        raise ValueError("Reporter omitted source coverage")
    expected_coverage = ({("hypothesis", hid) for hid in state["ledger"]["hypotheses"]}
                         | {("experiment", eid) for eid in state["ledger"]["experiments"]})
    actual_coverage = []
    for row in coverage:
        if not isinstance(row, dict) or row.get("kind") not in {"hypothesis", "experiment"}:
            raise ValueError("Each source coverage row must identify a hypothesis or experiment")
        if not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError("Each source coverage row must include a nonempty id")
        actual_coverage.append((row["kind"], row["id"]))
    if len(actual_coverage) != len(set(actual_coverage)) or set(actual_coverage) != expected_coverage:
        raise ValueError("Source coverage must include each hypothesis and experiment exactly once")
    state.update(status="complete", finished_at=now(), final_result=str(path), final_report=str(report))
    write(state_file, state)
    print(json.dumps({"status": "complete", "report": str(report), "experiments": len(state["rounds"])}))


if __name__ == "__main__":
    main()
