"""Offline invariants for claim coverage; no live novelty assessment."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
import idea_check as app
from functools import partial
from novelty_fixtures import claim_report as make_report
from novelty_contract import LEGACY_VERSION
claim_report = partial(make_report, version=LEGACY_VERSION)


class ClaimNovelty(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=PROJECT / "bootstrap")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.ideas = [{"id": "I1", "title": "Question", "idea": "Can a new state explain memory? Can the conditions be weakened?"}]
        self.result = claim_report(self.ideas, self.root, known_direction=True)
        self.check = self.result["checks"][0]
        self.novelty = self.check["novelty"]

    def validate(self):
        return app.validate_checks(self.result, self.ideas)

    def test_covered_question_needs_no_solution_or_equation(self):
        self.validate()

    def test_old_reports_are_readable_but_new_calls_cannot_downgrade(self):
        self.result.pop("schema_version")
        self.check.pop("novelty")
        app.validate_checks(self.result, self.ideas)
        with self.assertRaises(ValueError):
            app.validate_checks(self.result, self.ideas, require_claims=True)

    def test_unknown_schema_is_rejected(self):
        self.result["schema_version"] = "future-unknown"
        with self.assertRaises(ValueError):
            self.validate()

    def test_checker_cannot_invent_an_original_claim_quote(self):
        self.novelty["claims"][0]["idea_quote"] = "I guarantee universal optimality."
        with self.assertRaises(ValueError):
            self.validate()

    def test_invented_evidence_quote_is_rejected(self):
        self.novelty["evidence"][0]["quote"] = "A passage absent from the source."
        with self.assertRaises(ValueError):
            self.validate()

    def test_missing_source_snapshot_is_rejected(self):
        self.check["prior_work"]["sources"][0]["snapshot_path"] = str(self.root / "absent.txt")
        with self.assertRaises(ValueError):
            self.validate()

    def test_snapshot_cannot_escape_project(self):
        self.check["prior_work"]["sources"][0]["snapshot_path"] = "/etc/hosts"
        with self.assertRaises(ValueError):
            self.validate()

    def test_metadata_alone_cannot_establish_coverage(self):
        self.check["prior_work"]["sources"][0]["evidence_level"] = "metadata_only"
        with self.assertRaises(ValueError):
            self.validate()

    def test_evidence_from_another_source_cannot_support_this_source(self):
        source = copy.deepcopy(self.check["prior_work"]["sources"][0])
        source["source_id"] = "P2"
        self.check["prior_work"]["sources"].append(source)
        self.novelty["evidence"][0]["source_id"] = "P2"
        with self.assertRaises(ValueError):
            self.validate()

    def test_same_result_under_weaker_prior_assumptions_can_cover_theory(self):
        self.novelty["claims"][0]["kind"] = "theory"
        row = self.novelty["comparisons"][0]["claim_relations"][0]
        row["conditions"] = {"relation": "idea_implies_prior", "reason": "Synthetic example: bounded positive integers imply integers."}
        self.validate()

    def test_reverse_assumption_implication_cannot_cover_theory(self):
        self.novelty["claims"][0]["kind"] = "theory"
        row = self.novelty["comparisons"][0]["claim_relations"][0]
        row["conditions"] = {"relation": "prior_implies_idea", "reason": "Prior has stronger conditions."}
        with self.assertRaises(ValueError):
            self.validate()

    def test_same_direction_can_coexist_with_an_unresolved_contribution(self):
        self.add_second_claim()
        self.novelty["overall_status"] = "PARTIAL_OVERLAP"
        self.validate()
        self.assertEqual(self.check["prior_work"]["verdict"], "already_done")

    def add_second_claim(self):
        self.novelty["claims"].append({"claim_id": "C2", "text": "Weaker conditions?",
            "idea_quote": "Can the conditions be weakened?", "kind": "question", "coverage": "UNKNOWN"})
        self.novelty["comparisons"][0]["claim_relations"].append({"claim_id": "C2",
            "relation": "UNKNOWN", "reason": "No adequate passage.", "evidence_ids": [],
            "conditions": {"relation": "unknown", "reason": "Not specified."}})
        self.novelty["remaining_difference"] = [{"claim_id": "C2", "description": "Conditions remain unresolved."}]

    def test_module_coverage_from_different_papers_cannot_be_added_into_full_coverage(self):
        self.add_second_claim()
        p1 = self.novelty["comparisons"][0]
        source = copy.deepcopy(self.check["prior_work"]["sources"][0]); source["source_id"] = "P2"
        self.check["prior_work"]["sources"].append(source)
        ev = copy.deepcopy(self.novelty["evidence"][0]); ev.update(evidence_id="E2", source_id="P2")
        self.novelty["evidence"].append(ev)
        p2 = copy.deepcopy(p1); p2["source_id"] = "P2"
        for facet in p2["facets"].values():
            if facet["evidence_ids"]:
                facet["evidence_ids"] = ["E2"]
        p2["claim_relations"][0].update(relation="UNKNOWN", evidence_ids=[])
        p2["claim_relations"][1].update(relation="EQUIVALENT", evidence_ids=["E2"])
        self.novelty["comparisons"].append(p2)
        self.novelty["claims"][1]["coverage"] = "COVERED"
        self.novelty["remaining_difference"] = []
        # No source jointly covers both claims.
        with self.assertRaises(ValueError):
            self.validate()
        self.novelty["overall_status"] = "PARTIAL_OVERLAP"
        self.validate()

    def test_claimed_combination_must_be_identified(self):
        self.novelty["claims"][0]["kind"] = "combination"
        with self.assertRaises(ValueError):
            self.validate()
        self.novelty["combination_assessment"].update(status="assessed_as_claims", claim_ids=["C1"])
        self.validate()

    def test_no_coverage_found_requires_three_completed_retrieval_facets(self):
        self.result = claim_report(self.ideas, self.root / "negative")
        self.result["searches"].pop()
        with self.assertRaises(ValueError):
            self.validate()
        check = self.result["checks"][0]
        check["prior_work"]["verdict"] = "unclear"
        novelty = check["novelty"]
        novelty["claims"][0]["coverage"] = "UNKNOWN"
        novelty.update(overall_status="UNCLEAR", recommended_action="TARGETED_SEARCH")
        self.validate()

    def test_missing_method_in_abstract_can_remain_unknown(self):
        self.novelty["comparisons"][0]["claim_relations"][0].update(relation="UNKNOWN", evidence_ids=[])
        self.novelty["claims"][0]["coverage"] = "UNKNOWN"
        self.novelty.update(overall_status="UNCLEAR", recommended_action="TARGETED_SEARCH")
        self.validate()

    def test_covered_claim_cannot_be_returned_as_remaining_innovation(self):
        self.novelty["remaining_difference"] = [{"claim_id": "C1", "description": "Unsupported novelty claim."}]
        with self.assertRaises(ValueError):
            self.validate()

    def test_bounded_search_cannot_be_labelled_exhaustive(self):
        self.novelty["search_exhaustive"] = True
        with self.assertRaises(ValueError):
            self.validate()

    def test_search_response_must_be_saved(self):
        self.result["searches"][0]["snapshot_path"] = str(self.root / "missing_search.txt")
        with self.assertRaises(ValueError):
            self.validate()

    def test_unknown_evidence_cannot_trigger_early_coverage_stop(self):
        self.novelty["comparisons"][0]["claim_relations"][0].update(relation="UNKNOWN", evidence_ids=[])
        self.novelty["claims"][0]["coverage"] = "UNKNOWN"
        self.novelty.update(overall_status="UNCLEAR", recommended_action="TARGETED_SEARCH")
        self.novelty["search_summary"]["stop_reason"] = "sufficient_coverage"
        with self.assertRaises(ValueError):
            self.validate()


if __name__ == "__main__":
    unittest.main()
