"""Structural routing checks for anchor-linked experiment selection.

This guard checks declared fields and links only. It cannot determine whether a
plan is scientifically useful, novel, or truly discriminating.
"""
from __future__ import annotations


KINDS = {"target_test", "enabling_check", "calibration"}
REQUIRED_VALUE_FIELDS = {
    "kind", "unresolved_gap", "prior_work_boundary", "decision_relevance",
    "ready", "blockers", "enables_plan_id",
}


def _nonempty(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")


def validate_selection(result, expected_anchor=None):
    """Validate explicit anchor linkage and structural routing of planner actions."""
    if not isinstance(result, dict):
        raise ValueError("planner result must be an object")
    if result.get("decision") == "finalize":
        return None
    if result.get("decision") != "experiment":
        raise ValueError("guarded planner decision must be experiment or finalize")

    anchor = result.get("anchor_question")
    _nonempty(anchor, "anchor_question")
    if expected_anchor is not None:
        _nonempty(expected_anchor, "expected_anchor")
        if anchor != expected_anchor:
            raise ValueError("planner anchor_question differs from the fixed research anchor")

    plans = result.get("plans")
    if not isinstance(plans, list) or len(plans) < 1:
        raise ValueError("experiment decision requires at least one plan")
    by_id = {}
    for plan in plans:
        if not isinstance(plan, dict):
            raise ValueError("each proposed plan must be an object")
        plan_id = plan.get("id")
        _nonempty(plan_id, "plan.id")
        if plan_id in by_id:
            raise ValueError(f"duplicate plan id: {plan_id}")
        value = plan.get("research_value")
        if not isinstance(value, dict):
            raise ValueError(f"plan {plan_id} is missing research_value")
        missing = REQUIRED_VALUE_FIELDS - value.keys()
        if missing:
            raise ValueError(f"plan {plan_id} research_value is missing: {', '.join(sorted(missing))}")
        kind = value["kind"]
        if kind not in KINDS:
            raise ValueError(f"plan {plan_id} has an unknown research_value.kind")
        for field in ("unresolved_gap", "prior_work_boundary", "decision_relevance"):
            _nonempty(value[field], f"plan {plan_id} research_value.{field}")
        if not isinstance(value["ready"], bool):
            raise ValueError(f"plan {plan_id} research_value.ready must be boolean")
        blockers = value["blockers"]
        if not isinstance(blockers, list) or any(not isinstance(x, str) or not x.strip() for x in blockers):
            raise ValueError(f"plan {plan_id} blockers must be an array of nonempty strings")
        if len(blockers) != len(set(blockers)):
            raise ValueError(f"plan {plan_id} blockers must be unique")
        if value["ready"] and blockers:
            raise ValueError(f"ready plan {plan_id} cannot have unresolved blockers")
        if not value["ready"] and not blockers:
            raise ValueError(f"unready plan {plan_id} must name its blockers")
        enables = value["enables_plan_id"]
        resolves = value.get("resolves_blocker")
        if kind == "target_test":
            if enables is not None:
                raise ValueError(f"target test {plan_id} cannot enable another plan")
            if resolves is not None:
                raise ValueError(f"target test {plan_id} cannot declare resolves_blocker")
        else:
            if not isinstance(enables, str) or not enables.strip():
                raise ValueError(f"{kind} {plan_id} must identify the target plan it enables")
            _nonempty(resolves, f"plan {plan_id} research_value.resolves_blocker")
        by_id[plan_id] = plan

    targets = {pid: p for pid, p in by_id.items() if p["research_value"]["kind"] == "target_test"}
    if not targets:
        raise ValueError("planner must include at least one target_test plan")
    for plan_id, plan in by_id.items():
        value = plan["research_value"]
        if value["kind"] == "target_test":
            continue
        target = targets.get(value["enables_plan_id"])
        if target is None or target["research_value"]["ready"]:
            raise ValueError(f"{plan_id} must enable an unready target_test in this proposed list")
        if value["resolves_blocker"] not in target["research_value"]["blockers"]:
            raise ValueError(f"{plan_id} must name an exact blocker of its target_test")

    selected_id = result.get("selected_plan_id")
    if selected_id not in by_id:
        raise ValueError("selected_plan_id must name one of the proposed plans")
    selected = by_id[selected_id]["research_value"]
    if not selected["ready"]:
        raise ValueError("selected plan must be ready")
    if selected["kind"] != "target_test" and any(
        plan["research_value"]["kind"] == "target_test" and plan["research_value"]["ready"]
        for plan in plans
    ):
        raise ValueError("a ready target_test cannot be displaced by a non-target action")
    return None


def prompt_addendum(anchor_question):
    """Return planner instructions for keeping proposed actions tied to the anchor."""
    _nonempty(anchor_question, "anchor_question")
    return f"""Keep this exact fixed research anchor in `anchor_question`:
{anchor_question}

For every proposed plan, include `research_value` with `kind` (`target_test`,
`enabling_check`, or `calibration`), `unresolved_gap`, `prior_work_boundary`,
`decision_relevance`, boolean `ready`, string-array `blockers`, and nullable
`enables_plan_id`. A target test addresses the anchor directly. An enabling check
or calibration may be selected only to resolve a named blocker of an unready target
test in this same proposal list; include `resolves_blocker` with the exact blocker
text. Include at least one target test and select a ready plan. If a ready target
test is available, select it instead of an enabling check or calibration.

Before freezing any plan, check that the intervention actually includes every
regime, held-out shape, or repeat required by its decisive outcome classes. Correct
an inconsistent plan before execution, or make the registered conclusion explicitly
inconclusive. Explain which decision each plausible result would change. These fields
are routing context, not a numeric utility score or a guarantee of novelty or scientific
discrimination; those still need evidence and review."""
