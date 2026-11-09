"""Immutable hypothesis and predeclared-evidence ledger helpers."""
from __future__ import annotations

from copy import deepcopy
import math
import re


HYPOTHESIS_STATUSES = {
    "untested", "supported", "contradicted", "mixed", "inconclusive", "stale"
}
EFFECTS = {"supports", "contradicts", "inconclusive"}
PLAN_FIELDS = (
    "id", "question", "hypothesis_ids", "intervention", "outcome_measure",
    "predictions", "outcome_classes", "cost_minutes", "feasibility",
    "selection_reason", "replication",
)


def empty_ledger():
    return {"hypotheses": {}, "evidence": [], "experiments": {}, "revision": 0}


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")


def _identifier(value, label):
    _text(value, label)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError(f"{label} must be a simple identifier without path separators")


def _ledger(ledger):
    if not isinstance(ledger, dict) or not all(
        isinstance(ledger.get(k), typ) for k, typ in (
            ("hypotheses", dict), ("evidence", list), ("experiments", dict)
        )
    ):
        raise ValueError("ledger must contain hypotheses, evidence, and experiments")
    if not isinstance(ledger.get("revision", 0), int) or isinstance(ledger.get("revision", 0), bool):
        raise ValueError("ledger revision must be an integer")


def _plan_snapshot(plan):
    return {key: deepcopy(plan[key]) for key in PLAN_FIELDS if key in plan}


def _stored_plan(experiment):
    return experiment.get("plan", experiment)


def _same_plan(stored, plan):
    return _plan_snapshot(stored) == _plan_snapshot(plan)


def apply_proposals(ledger, proposals, source):
    """Append new, attributed hypotheses without changing existing records."""
    _ledger(ledger)
    _text(source, "source")
    if not isinstance(proposals, (list, tuple)):
        raise ValueError("proposals must be a list")
    result = deepcopy(ledger)
    pending = set()
    for proposal in proposals:
        if not isinstance(proposal, dict):
            raise ValueError("each proposal must be an object")
        for key in ("id", "statement", "representation", "measurement"):
            _text(proposal.get(key), f"proposal.{key}")
        hid = proposal["id"]
        _identifier(hid, "proposal.id")
        if hid in result["hypotheses"] or hid in pending:
            raise ValueError(f"hypothesis id is immutable and already used: {hid}")
        if proposal.get("status", "proposed") != "proposed":
            raise ValueError("new proposals must have status 'proposed'")
        for key in ("predictions", "alternatives", "prior_work"):
            if key in proposal and not isinstance(proposal[key], (list, tuple)):
                raise ValueError(f"proposal.{key} must be an array")
        parent_id = proposal.get("parent_id")
        if parent_id is not None:
            _identifier(parent_id, "proposal.parent_id")
        if parent_id is not None and parent_id not in result["hypotheses"] and parent_id not in pending:
            raise ValueError(f"unknown parent hypothesis: {parent_id}")
        depends_on = proposal.get("depends_on", [])
        if not isinstance(depends_on, (list, tuple)):
            raise ValueError("proposal.depends_on must be an array of distinct hypothesis ids")
        for dependency in depends_on:
            _identifier(dependency, "proposal.depends_on item")
        if len(set(depends_on)) != len(depends_on):
            raise ValueError("proposal.depends_on must be an array of distinct hypothesis ids")
        if hid in depends_on or any(dependency not in ledger["hypotheses"] for dependency in depends_on):
            raise ValueError("depends_on must reference already-existing hypotheses other than itself")
        pending.add(hid)
        record = deepcopy(proposal)
        record.update(status="untested", evidence_ids=[], source=source)
        result["hypotheses"][hid] = record
    if proposals:
        result["revision"] = result.get("revision", 0) + 1
    return result


def validate_experiment(ledger, plan):
    """Validate the structure of a discriminating plan; this is not science review."""
    _ledger(ledger)
    if not isinstance(plan, dict):
        raise ValueError("plan must be an object")
    for key in PLAN_FIELDS[:-1]:
        if key not in plan:
            raise ValueError(f"plan.{key} is required")
    for key in ("id", "question", "intervention", "outcome_measure", "feasibility", "selection_reason"):
        _text(plan.get(key), f"plan.{key}")
    _identifier(plan["id"], "plan.id")
    ids = plan["hypothesis_ids"]
    if not isinstance(ids, (list, tuple)) or len(ids) < 2 or len(set(ids)) != len(ids):
        raise ValueError("plan.hypothesis_ids must contain at least two distinct ids")
    if any(hid not in ledger["hypotheses"] for hid in ids):
        raise ValueError("plan references an unknown hypothesis")
    cost = plan["cost_minutes"]
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
        raise ValueError("plan.cost_minutes must be a finite nonnegative number")
    if "replication" in plan and not isinstance(plan["replication"], bool):
        raise ValueError("plan.replication must be boolean")

    predictions = plan["predictions"]
    if not isinstance(predictions, (list, tuple)) or not predictions:
        raise ValueError("plan.predictions must be a nonempty array")
    predicted_hypotheses = set()
    prediction_outcomes = set()
    for prediction in predictions:
        if not isinstance(prediction, dict):
            raise ValueError("each prediction must be an object")
        hid = prediction.get("hypothesis_id")
        if hid not in ids:
            raise ValueError("prediction references a hypothesis outside the plan")
        _text(prediction.get("expected_outcome"), "prediction.expected_outcome")
        _text(prediction.get("outcome_id"), "prediction.outcome_id")
        predicted_hypotheses.add(hid)
        prediction_outcomes.add(prediction["outcome_id"])
    if predicted_hypotheses != set(ids):
        raise ValueError("predictions must cover every planned hypothesis")
    if len(prediction_outcomes) < 2:
        raise ValueError("predictions must predeclare at least two distinct outcomes")

    classes = plan["outcome_classes"]
    if not isinstance(classes, (list, tuple)) or not classes:
        raise ValueError("plan.outcome_classes must be a nonempty array")
    class_ids = set()
    separating = False
    for outcome in classes:
        if not isinstance(outcome, dict):
            raise ValueError("each outcome class must be an object")
        outcome_id = outcome.get("id")
        _text(outcome_id, "outcome_class.id")
        _text(outcome.get("description"), "outcome_class.description")
        if outcome_id in class_ids:
            raise ValueError("outcome class ids must be unique")
        class_ids.add(outcome_id)
        effects = outcome.get("effects")
        if not isinstance(effects, dict) or set(effects) != set(ids):
            raise ValueError("each outcome class must define effects for every hypothesis")
        if any(effect not in EFFECTS for effect in effects.values()):
            raise ValueError("outcome effects must be supports, contradicts, or inconclusive")
        if len(set(effects.values())) > 1:
            separating = True
    if not prediction_outcomes <= class_ids:
        raise ValueError("every predicted outcome must have a predeclared outcome class")
    if not any(all(effect == "inconclusive" for effect in item["effects"].values()) for item in classes):
        raise ValueError("outcome classes must include an explicitly inconclusive class")
    if not separating:
        raise ValueError("at least one outcome class must meaningfully separate hypotheses")

    prior = ledger["experiments"].get(plan["id"])
    if prior is not None and not _same_plan(_stored_plan(prior), plan):
        raise ValueError(f"experiment plan is frozen: {plan['id']}")
    return None


def _evidence_status(records):
    supports = any(record == "supports" for record in records)
    contradicts = any(record == "contradicts" for record in records)
    inconclusive = any(record == "inconclusive" for record in records)
    if supports and contradicts:
        return "mixed"
    if supports:
        return "supported"
    if contradicts:
        return "contradicted"
    if inconclusive:
        return "inconclusive"
    return "untested"


def _mark_descendants_stale(hypotheses, parent_id):
    queue = [parent_id]
    visited = set()
    while queue:
        changed_parent = queue.pop(0)
        for hid, hypothesis in hypotheses.items():
            if hid in visited or changed_parent not in hypothesis.get("depends_on", []):
                continue
            visited.add(hid)
            hypothesis["status"] = "stale"
            hypothesis["stale_warning"] = {
                "parent_id": changed_parent,
                "reason": "a required hypothesis became contradicted or mixed",
            }
            queue.append(hid)


def apply_observations(ledger, plan, observation, source):
    """Record a result against its frozen plan and update statuses deterministically."""
    validate_experiment(ledger, plan)
    _text(source, "source")
    if not isinstance(observation, dict):
        raise ValueError("observation must be an object")
    if observation.get("experiment_id") != plan["id"]:
        raise ValueError("observation experiment_id must match the plan")
    status = observation.get("execution_status")
    if status not in {"completed", "partial", "failed"}:
        raise ValueError("execution_status must be completed, partial, or failed")
    _text(observation.get("summary"), "observation.summary")
    artifacts = observation.get("artifacts", [])
    limitations = observation.get("limitations", [])
    if not isinstance(artifacts, list) or not isinstance(limitations, list):
        raise ValueError("artifacts and limitations must be arrays")
    if "hypothesis_updates" in observation:
        raise ValueError("hypothesis_updates are prohibited; effects come from the frozen plan")
    outcome_id = observation.get("observed_outcome_id")
    class_ids = {item["id"] for item in plan["outcome_classes"]}
    if outcome_id not in class_ids and outcome_id != "unclassified":
        raise ValueError("observed_outcome_id must be a predeclared class or 'unclassified'")

    result = deepcopy(ledger)
    prior = result["experiments"].get(plan["id"])
    if prior is not None and prior.get("observation") is not None:
        raise ValueError(f"experiment already has a result: {plan['id']}")
    plan_copy = deepcopy(plan)
    evidence_id = f"{plan['id']}:result"
    if any(item.get("id") == evidence_id for item in result["evidence"]):
        raise ValueError(f"duplicate evidence result: {evidence_id}")

    if status == "completed" and outcome_id in class_ids:
        effects = next(item["effects"] for item in plan["outcome_classes"] if item["id"] == outcome_id)
    else:
        effects = {hid: "inconclusive" for hid in plan["hypothesis_ids"]}
    evidence = {
        "id": evidence_id,
        "experiment_id": plan["id"],
        "execution_status": status,
        "observed_outcome_id": outcome_id,
        "summary": observation["summary"],
        "artifacts": deepcopy(artifacts),
        "limitations": deepcopy(limitations),
        "relations": deepcopy(effects),
        "source": source,
    }
    result["evidence"].append(evidence)
    for hid, relation in effects.items():
        result["hypotheses"][hid].setdefault("evidence_ids", []).append(evidence_id)

    if prior is None:
        result["experiments"][plan["id"]] = {"plan": plan_copy, "observation": deepcopy(observation)}
    else:
        prior["observation"] = deepcopy(observation)

    for hid in effects:
        hypothesis = result["hypotheses"][hid]
        relations = [item["relations"][hid] for item in result["evidence"] if hid in item["relations"]]
        new_status = _evidence_status(relations)
        if hypothesis.get("status") != "stale" or "stale_warning" in hypothesis:
            hypothesis["status"] = new_status
        if new_status in {"contradicted", "mixed"}:
            _mark_descendants_stale(result["hypotheses"], hid)

    result["revision"] = result.get("revision", 0) + 1
    return result
