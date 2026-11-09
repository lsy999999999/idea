import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))

import discover_v2
from hypothesis_ledger import apply_observations, apply_proposals, empty_ledger


def proposal(hid):
    return {
        "id": hid,
        "statement": f"Mechanism {hid} changes response under a controlled intervention.",
        "representation": f"state_{hid}",
        "measurement": f"measure_{hid}",
        "predictions": ["response", "no response"],
        "alternatives": ["baseline explanation"],
        "prior_work": [],
        "status": "proposed",
    }


def experiment_plan(eid):
    return {
        "id": eid,
        "question": "Which explanation predicts the response?",
        "hypothesis_ids": ["A1", "B1"],
        "intervention": "apply the planned intervention",
        "outcome_measure": "response magnitude",
        "predictions": [
            {"hypothesis_id": "A1", "expected_outcome": "response", "outcome_id": "response"},
            {"hypothesis_id": "B1", "expected_outcome": "no response", "outcome_id": "no_response"},
        ],
        "outcome_classes": [
            {"id": "response", "description": "response threshold met", "effects": {"A1": "supports", "B1": "contradicts"}},
            {"id": "no_response", "description": "response threshold not met", "effects": {"A1": "contradicts", "B1": "supports"}},
            {"id": "uncertain", "description": "measurement is ambiguous", "effects": {"A1": "inconclusive", "B1": "inconclusive"}},
        ],
        "cost_minutes": 15,
        "feasibility": "the local setup is available",
        "selection_reason": "the explanations predict different measured outcomes",
        "replication": False,
    }


class FakeStages:
    def __init__(self, review_mode="valid", invalid_planner=False, invalid_coverage=False, timeouts=()):
        self.calls = []
        self.seed_tasks = {}
        self.timeouts = set(timeouts)
        self.review_mode = review_mode
        self.invalid_planner = invalid_planner
        self.invalid_coverage = invalid_coverage
        self.planner_saw_latest_evidence = False
        self.plan_was_frozen = False
        self.selection_repair_received_rejection = False
        self.failed_result_status = None

    def __call__(self, run, stage, role, task, inputs, model, effort, timeout):
        run = Path(run)
        inputs = [Path(item) for item in inputs]
        self.calls.append(stage)
        if stage in self.timeouts:
            workspace = run / "fake_stages" / stage
            workspace.mkdir(parents=True, exist_ok=True)
            result_path = workspace / "result.json"
            result_path.write_text(json.dumps({"execution_status": "timed_out", "summary": "Simulated timeout."}))
            (workspace / "attempt.txt").write_text(f"preserved:{stage}")
            return result_path, json.loads(result_path.read_text())
        if stage.startswith("seed_A"):
            self.seed_tasks[stage] = task
            result = {"proposals": [proposal("A1")]}
        elif stage == "seed_B":
            self.seed_tasks[stage] = task
            result = {"proposals": [proposal("B1")]}
        elif stage == "bridge":
            result = {"proposals": []}
        elif stage == "plan_00":
            p1, p2 = experiment_plan("E1"), experiment_plan("E2")
            if self.invalid_planner:
                p1["predictions"][1]["outcome_id"] = "response"
            result = {"decision": "experiment", "proposals": [], "plans": [p1, p2],
                      "selected_plan_id": "E1", "selection_reason": "different predictions"}
        elif stage == "plan_00_selection_repair":
            rejection = next(p for p in inputs if p.name == "selection_rejection_00.json")
            rejection_data = json.loads(rejection.read_text())
            self.selection_repair_received_rejection = (
                "anchor_question" in rejection_data["error"]
                and rejection.is_file()
            )
            p1, p2 = experiment_plan("E1"), experiment_plan("E2")
            p1["research_value"] = {
                "kind": "target_test", "unresolved_gap": "policy value across schedule regimes",
                "prior_work_boundary": "known end-mark behavior does not establish policy value",
                "decision_relevance": "determines whether a policy comparison is warranted",
                "ready": True, "blockers": [], "enables_plan_id": None,
            }
            p2["research_value"] = {
                "kind": "target_test", "unresolved_gap": "policy value across schedule regimes",
                "prior_work_boundary": "known end-mark behavior does not establish policy value",
                "decision_relevance": "could follow once the target schedule is available",
                "ready": False, "blockers": ["obtain an independent schedule trace"],
                "enables_plan_id": None,
            }
            anchor = next(p for p in inputs if p.name == "anchor.md").read_text().strip()
            result = {"decision": "experiment", "anchor_question": anchor,
                      "proposals": [], "plans": [p1, p2], "selected_plan_id": "E1",
                      "selection_reason": "the ready plan directly tests the anchor"}
        elif stage == "experiment_00":
            plan_path = next(p for p in inputs if p.name == "00_E1.json")
            receipt = run / "frozen_plans/00_receipt.json"
            frozen = json.loads(plan_path.read_text())
            receipt_data = json.loads(receipt.read_text()) if receipt.is_file() else {}
            self.plan_was_frozen = (receipt.is_file()
                and frozen["outcome_classes"][-1]["id"] == "uncertain"
                and receipt_data.get("sha256") == hashlib.sha256(plan_path.read_bytes()).hexdigest())
            result = {"observation": {
                "experiment_id": "E1", "execution_status": "failed",
                "observed_outcome_id": "uncertain", "summary": "Execution failed before measurement.",
                "artifacts": [], "limitations": ["No scientific result was obtained."],
            }}
        elif stage == "plan_01":
            ledger_path = next(p for p in inputs if p.name == "ledger_01.json")
            ledger = json.loads(ledger_path.read_text())
            self.planner_saw_latest_evidence = (
                len(ledger["evidence"]) == 1
                and ledger["evidence"][0]["execution_status"] == "failed"
                and all(h["status"] == "inconclusive" for h in ledger["hypotheses"].values())
            )
            result = {"decision": "finalize", "proposals": [], "plans": [], "selected_plan_id": None}
        elif stage == "review":
            finding = {"experiment_id": "E1", "classification_valid": True,
                       "reason": "Failed execution yielded no classification.", "evidence_paths": []}
            if self.review_mode == "missing":
                result = {"review_findings": []}
            elif self.review_mode == "duplicate":
                result = {"review_findings": [finding, dict(finding)]}
            else:
                result = {"review_findings": [finding]}
        elif stage == "report":
            result = {"source_coverage": [
                {"kind": "hypothesis", "id": "A1"},
                {"kind": "hypothesis", "id": "B1"},
                {"kind": "experiment", "id": "E1"},
            ]}
            if self.invalid_coverage:
                result["source_coverage"].append({"kind": "experiment", "id": "E1"})
        else:
            raise AssertionError(f"unexpected stage: {stage}")

        workspace = run / "fake_stages" / stage
        workspace.mkdir(parents=True, exist_ok=True)
        result_path = workspace / "result.json"
        result_path.write_text(json.dumps(result))
        if stage == "report":
            (workspace / "REPORT.md").write_text("测试报告")
        return result_path, result


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=PROJECT)
        self.root = Path(self.temp.name)
        self.brief = self.root / "brief.md"
        self.brief.write_text("A bounded test brief.")
        self.run = self.root / "run"
        self.argv = ["discover_v2.py", "--brief", str(self.brief), "--run-dir", str(self.run),
                     "--max-experiments", "2"]

    def tearDown(self):
        self.temp.cleanup()

    def run_controller(self, fake):
        with patch.object(sys, "argv", self.argv), patch.object(discover_v2, "stage_run", fake), contextlib.redirect_stdout(io.StringIO()):
            discover_v2.main()

    def test_full_loop_freezes_plan_passes_latest_evidence_and_resumes_without_calls(self):
        fake = FakeStages()
        self.run_controller(fake)
        self.assertIn("smallest predictive state", fake.seed_tasks["seed_A"])
        self.assertIn("strongest simple known baseline", fake.seed_tasks["seed_B"])
        self.assertNotEqual(fake.seed_tasks["seed_A"], fake.seed_tasks["seed_B"])
        self.assertTrue(fake.plan_was_frozen)
        self.assertTrue(fake.planner_saw_latest_evidence)
        state = json.loads((self.run / "v2_state.json").read_text())
        self.assertEqual(state["ledger"]["hypotheses"]["A1"]["status"], "inconclusive")
        self.assertEqual(state["ledger"]["hypotheses"]["B1"]["status"], "inconclusive")
        calls_before_resume = list(fake.calls)
        self.run_controller(fake)
        self.assertEqual(fake.calls, calls_before_resume)

    def test_invalid_planner_plan_is_rejected_before_execution(self):
        fake = FakeStages(invalid_planner=True)
        with self.assertRaises(ValueError):
            self.run_controller(fake)
        self.assertNotIn("experiment_00", fake.calls)

    def test_guard_rejects_and_repairs_selection_before_experiment(self):
        anchor_file = self.root / "anchor.md"
        anchor_file.write_text("Can public signals improve policy value across reader-release schedules?")
        self.argv.extend(["--anchor-file", str(anchor_file)])
        fake = FakeStages()
        self.run_controller(fake)
        self.assertEqual(fake.calls.count("plan_00_selection_repair"), 1)
        self.assertTrue(fake.selection_repair_received_rejection)
        self.assertLess(fake.calls.index("plan_00_selection_repair"), fake.calls.index("experiment_00"))
        self.assertTrue((self.run / "dispatch/selection_rejection_00.json").is_file())
        receipt = json.loads((self.run / "frozen_plans/00_receipt.json").read_text())
        self.assertIn("plan_00_selection_repair", receipt["planner_result"])

    def test_seed_timeout_retries_once_under_distinct_id_and_preserves_original(self):
        fake = FakeStages(timeouts={"seed_A"})
        self.run_controller(fake)
        self.assertEqual(fake.calls[:3], ["seed_A", "seed_A_retry1", "seed_B"])
        self.assertTrue((self.run / "fake_stages/seed_A/attempt.txt").is_file())
        state = json.loads((self.run / "v2_state.json").read_text())
        self.assertIn("seed_A_retry1", state["seeds"][0])

    def test_second_reasoning_timeout_raises_and_keeps_both_attempts(self):
        fake = FakeStages(timeouts={"seed_A", "seed_A_retry1"})
        with self.assertRaisesRegex(RuntimeError, "after two bounded attempts"):
            self.run_controller(fake)
        self.assertEqual(fake.calls, ["seed_A", "seed_A_retry1"])
        self.assertTrue((self.run / "fake_stages/seed_A/attempt.txt").is_file())
        self.assertTrue((self.run / "fake_stages/seed_A_retry1/attempt.txt").is_file())

    def test_experimental_timeout_becomes_inconclusive_without_retry(self):
        fake = FakeStages(timeouts={"experiment_00"})
        self.run_controller(fake)
        self.assertEqual(fake.calls.count("experiment_00"), 1)
        self.assertNotIn("experiment_00_retry1", fake.calls)
        state = json.loads((self.run / "v2_state.json").read_text())
        evidence = state["ledger"]["evidence"][0]
        self.assertEqual(evidence["execution_status"], "failed")
        self.assertTrue(all(value == "inconclusive" for value in evidence["relations"].values()))
        self.assertTrue((self.run / "fake_stages/experiment_00/attempt.txt").is_file())

    def test_missing_and_duplicate_reviewer_rows_are_rejected(self):
        for mode in ("missing", "duplicate"):
            with self.subTest(mode=mode):
                self.tearDown()
                self.setUp()
                fake = FakeStages(review_mode=mode)
                with self.assertRaises(ValueError):
                    self.run_controller(fake)

    def test_reporter_must_cover_each_hypothesis_and_experiment_once(self):
        fake = FakeStages(invalid_coverage=True)
        with self.assertRaises(ValueError):
            self.run_controller(fake)

    def test_review_flags_only_hypotheses_in_actual_experiment_evidence(self):
        ledger = apply_proposals(empty_ledger(), [proposal("A1"), proposal("B1"), proposal("C1")], "seed")
        ledger = apply_proposals(ledger, [
            {**proposal("D1"), "parent_id": "A1", "depends_on": ["A1"]},
            {**proposal("F1"), "parent_id": "B1"},
        ], "theorist")
        ledger = apply_proposals(ledger, [{**proposal("E1"), "depends_on": ["D1"]}], "theorist")
        plan = experiment_plan("E1")
        ledger = apply_observations(ledger, plan, {
            "experiment_id": "E1", "execution_status": "failed", "observed_outcome_id": "uncertain",
            "summary": "No execution result.", "artifacts": [], "limitations": [],
        }, "executor")
        reviewed = discover_v2.add_review(ledger, [{"experiment_id": "E1", "classification_valid": None,
            "reason": "uncertain classification", "evidence_paths": []}], "reviewer")
        self.assertEqual(reviewed["hypotheses"]["A1"]["review_status"], "needs_review")
        self.assertEqual(reviewed["hypotheses"]["B1"]["review_status"], "needs_review")
        self.assertEqual(reviewed["hypotheses"]["D1"]["review_status"], "needs_review")
        self.assertEqual(reviewed["hypotheses"]["E1"]["review_status"], "needs_review")
        self.assertNotIn("review_status", reviewed["hypotheses"]["F1"])
        self.assertNotIn("review_status", reviewed["hypotheses"]["C1"])
        self.assertEqual(ledger["hypotheses"]["A1"]["review_status"] if "review_status" in ledger["hypotheses"]["A1"] else None, None)


if __name__ == "__main__":
    unittest.main()
