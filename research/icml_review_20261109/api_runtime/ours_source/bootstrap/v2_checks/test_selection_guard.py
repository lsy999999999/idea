import copy
import sys
from pathlib import Path
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))

from selection_guard import prompt_addendum, validate_selection


ANCHOR = "Can observable signals improve checkpoint cost across reader-release and write-burst schedules?"


def value(kind, *, ready=True, blockers=None, enables=None, resolves=None):
    result = {
        "kind": kind,
        "unresolved_gap": "Whether the signal changes the scheduling decision.",
        "prior_work_boundary": "Known WAL behavior does not establish policy value.",
        "decision_relevance": "Would change whether to schedule this policy.",
        "ready": ready,
        "blockers": [] if blockers is None and ready else (blockers or []),
        "enables_plan_id": enables,
    }
    if resolves is not None:
        result["resolves_blocker"] = resolves
    return result


def plan(plan_id, research_value):
    return {"id": plan_id, "research_value": research_value}


def result(plans, selected):
    return {"decision": "experiment", "anchor_question": ANCHOR,
            "plans": plans, "selected_plan_id": selected}


class SelectionGuardTests(unittest.TestCase):
    def test_ready_target_test_wins_over_other_ready_actions(self):
        target = plan("E1", value("target_test"))
        calibration = plan("E2", value("calibration", enables="E3", resolves="unavailable regime"))
        unready = plan("E3", value("target_test", ready=False, blockers=["unavailable regime"]))
        candidate = result([target, calibration, unready], "E1")
        self.assertIsNone(validate_selection(candidate, ANCHOR))
        with self.assertRaises(ValueError):
            validate_selection({**candidate, "selected_plan_id": "E2"}, ANCHOR)

    def test_valid_enabling_check_may_be_selected_when_target_is_blocked(self):
        blocker = "confirm held-out schedule generator"
        target = plan("E1", value("target_test", ready=False, blockers=[blocker]))
        check = plan("E2", value("enabling_check", enables="E1", resolves=blocker))
        self.assertIsNone(validate_selection(result([target, check], "E2"), ANCHOR))

    def test_unmatched_or_ready_target_enabler_is_rejected(self):
        target = plan("E1", value("target_test", ready=False, blockers=["confirm measurement"]))
        check = plan("E2", value("calibration", enables="E1", resolves="different blocker"))
        with self.assertRaises(ValueError):
            validate_selection(result([target, check], "E2"), ANCHOR)
        ready_target = plan("E3", value("target_test"))
        with self.assertRaises(ValueError):
            validate_selection(result([ready_target, target, check], "E2"), ANCHOR)

    def test_requires_target_and_exact_anchor(self):
        calibration = plan("E1", value("calibration", enables="E2", resolves="block"))
        with self.assertRaises(ValueError):
            validate_selection(result([calibration], "E1"), ANCHOR)
        candidate = result([plan("E1", value("target_test"))], "E1")
        with self.assertRaises(ValueError):
            validate_selection(candidate, ANCHOR + " changed")
        candidate["anchor_question"] = "  "
        with self.assertRaises(ValueError):
            validate_selection(candidate, ANCHOR)

    def test_missing_value_fields_and_unready_selected_plan_are_rejected(self):
        incomplete = value("target_test")
        del incomplete["decision_relevance"]
        with self.assertRaises(ValueError):
            validate_selection(result([plan("E1", incomplete)], "E1"), ANCHOR)
        blocked = plan("E1", value("target_test", ready=False, blockers=["measurement unavailable"]))
        with self.assertRaises(ValueError):
            validate_selection(result([blocked], "E1"), ANCHOR)

    def test_finalize_remains_outside_selection_routing_and_prompt_makes_no_claim(self):
        self.assertIsNone(validate_selection({"decision": "finalize", "plans": [], "selected_plan_id": None}, ANCHOR))
        original = result([plan("E1", value("target_test"))], "E1")
        before = copy.deepcopy(original)
        self.assertIsNone(validate_selection(original, ANCHOR))
        self.assertEqual(original, before)
        prompt = prompt_addendum(ANCHOR)
        self.assertIn(ANCHOR, prompt)
        self.assertIn("not a numeric utility score", prompt)
        with self.assertRaises(ValueError):
            prompt_addendum("  ")


if __name__ == "__main__":
    unittest.main()
