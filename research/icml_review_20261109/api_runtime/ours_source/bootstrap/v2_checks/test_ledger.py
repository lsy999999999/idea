import copy
import unittest

from src.hypothesis_ledger import (
    apply_observations,
    apply_proposals,
    empty_ledger,
    validate_experiment,
)


def proposal(hid, parent_id=None, depends_on=None):
    item = {
        "id": hid,
        "statement": f"Mechanism {hid} changes measured outcome under intervention.",
        "representation": f"state_{hid}",
        "measurement": f"measure_{hid}",
        "predictions": ["increase", "decrease"],
        "alternatives": ["baseline explanation"],
        "prior_work": [],
        "status": "proposed",
    }
    if parent_id:
        item["parent_id"] = parent_id
    if depends_on is not None:
        item["depends_on"] = depends_on
    return item


def plan(experiment_id="e1"):
    return {
        "id": experiment_id,
        "question": "Which account predicts a response to the intervention?",
        "hypothesis_ids": ["h1", "h2"],
        "intervention": "apply intervention",
        "outcome_measure": "response magnitude",
        "predictions": [
            {"hypothesis_id": "h1", "expected_outcome": "response", "outcome_id": "response"},
            {"hypothesis_id": "h2", "expected_outcome": "no response", "outcome_id": "no_response"},
        ],
        "outcome_classes": [
            {"id": "response", "description": "response observed", "effects": {"h1": "supports", "h2": "contradicts"}},
            {"id": "no_response", "description": "no response observed", "effects": {"h1": "contradicts", "h2": "supports"}},
            {"id": "uncertain", "description": "measurement is ambiguous", "effects": {"h1": "inconclusive", "h2": "inconclusive"}},
        ],
        "cost_minutes": 20,
        "feasibility": "available locally",
        "selection_reason": "the accounts predict different outcomes",
    }


def seeded_ledger():
    return apply_proposals(empty_ledger(), [proposal("h1"), proposal("h2")], "theorist")


def observation(exp="e1", status="completed", outcome="response"):
    return {
        "experiment_id": exp,
        "execution_status": status,
        "observed_outcome_id": outcome,
        "summary": "Recorded outcome from the predeclared procedure.",
        "artifacts": [],
        "limitations": [],
    }


class LedgerTests(unittest.TestCase):
    def test_proposals_are_attributed_immutable_and_inputs_unchanged(self):
        original = empty_ledger()
        new = apply_proposals(original, [proposal("h1")], "theorist")
        self.assertEqual(original["hypotheses"], {})
        self.assertEqual(new["hypotheses"]["h1"]["status"], "untested")
        self.assertEqual(new["hypotheses"]["h1"]["source"], "theorist")
        with self.assertRaises(ValueError):
            apply_proposals(new, [proposal("h1")], "reviewer")

    def test_validation_requires_structurally_discriminating_predictions(self):
        ledger = seeded_ledger()
        valid = plan()
        self.assertIsNone(validate_experiment(ledger, valid))
        bad = copy.deepcopy(valid)
        bad["predictions"][1]["outcome_id"] = "response"
        with self.assertRaises(ValueError):
            validate_experiment(ledger, bad)

    def test_identifiers_cannot_escape_plan_artifact_directory(self):
        with self.assertRaises(ValueError):
            apply_proposals(empty_ledger(), [proposal("../outside")], "theorist")
        bad = plan("../outside")
        with self.assertRaises(ValueError):
            validate_experiment(seeded_ledger(), bad)

    def test_failed_execution_is_inconclusive_not_refutation(self):
        ledger = seeded_ledger()
        result = apply_observations(ledger, plan(), observation(status="failed", outcome="response"), "executor")
        self.assertEqual(result["hypotheses"]["h1"]["status"], "inconclusive")
        self.assertEqual(result["hypotheses"]["h2"]["status"], "inconclusive")
        self.assertEqual(result["evidence"][0]["relations"], {"h1": "inconclusive", "h2": "inconclusive"})
        self.assertEqual(ledger["evidence"], [])

    def test_contradiction_stales_only_explicit_dependents_and_mixed_evidence_is_retained(self):
        ledger = apply_proposals(seeded_ledger(), [proposal("h1_revision", "h1")], "theorist")
        ledger = apply_proposals(ledger, [proposal("h1_dependent", "h1", ["h1"])], "theorist")
        ledger = apply_proposals(ledger, [proposal("h1_grandchild", depends_on=["h1_dependent"])], "theorist")
        p1 = plan("e1")
        out = apply_observations(ledger, p1, observation("e1", outcome="no_response"), "executor")
        self.assertEqual(out["hypotheses"]["h1"]["status"], "contradicted")
        self.assertEqual(out["hypotheses"]["h1_revision"]["status"], "untested")
        self.assertEqual(out["hypotheses"]["h1_dependent"]["status"], "stale")
        self.assertEqual(out["hypotheses"]["h1_dependent"]["stale_warning"]["parent_id"], "h1")
        self.assertEqual(out["hypotheses"]["h1_grandchild"]["status"], "stale")

        p2 = plan("e2")
        # Reuse the same two hypotheses and a distinct frozen experiment.
        out2 = apply_observations(out, p2, observation("e2", outcome="response"), "independent reviewer")
        self.assertEqual(out2["hypotheses"]["h1"]["status"], "mixed")
        self.assertEqual(len(out2["hypotheses"]["h1"]["evidence_ids"]), 2)

    def test_depends_on_requires_existing_ids_and_cannot_form_cycles(self):
        with self.assertRaises(ValueError):
            apply_proposals(seeded_ledger(), [proposal("h3", depends_on=["h4"]), proposal("h4")], "theorist")
        with self.assertRaises(ValueError):
            apply_proposals(seeded_ledger(), [proposal("h3", depends_on=["h3"])], "theorist")

    def test_plan_is_frozen_and_result_uses_declared_effects_only(self):
        ledger = seeded_ledger()
        result = apply_observations(ledger, plan(), observation(), "executor")
        changed = copy.deepcopy(plan())
        changed["outcome_classes"][0]["effects"]["h1"] = "contradicts"
        with self.assertRaises(ValueError):
            validate_experiment(result, changed)
        forged = observation()
        forged["hypothesis_updates"] = {"h1": "contradicts"}
        with self.assertRaises(ValueError):
            apply_observations(ledger, plan(), forged, "executor")
        self.assertEqual(result["hypotheses"]["h1"]["status"], "supported")
        with self.assertRaises(ValueError):
            apply_observations(result, plan(), observation(), "executor")

    def test_unclassified_and_partial_results_do_not_contradict(self):
        for status, outcome in (("partial", "response"), ("completed", "unclassified")):
            result = apply_observations(seeded_ledger(), plan(), observation(status=status, outcome=outcome), "executor")
            self.assertTrue(all(h["status"] == "inconclusive" for h in result["hypotheses"].values()))


if __name__ == "__main__":
    unittest.main()
