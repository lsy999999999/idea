"""Temporal novelty and hidden-source rediscovery invariants, using synthetic evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
import idea_check as app
from novelty_contract import FACETS, LEGACY_VERSION
from novelty_fixtures import claim_report, scope_report


class NoveltyScope(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=PROJECT / "bootstrap")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.idea = {"id": "I1", "title": "Memory question", "idea": "Can a state explain memory?"}
        self.result = claim_report([self.idea], self.root, known_direction=True)
        self.check = self.result["checks"][0]
        self.novelty = self.check["novelty"]
        self.source = self.check["prior_work"]["sources"][0]
        self.source["publication_date"] = self.date_record("2020-01-01")
        self.context = {"mode": "historical", "reference_date": self.date_record("2020-01-01"),
                        "reference_reason": "Synthetic source-paper first public release.", "source_papers": []}
        self.idea["evaluation_context"] = self.context

    def date_record(self, earliest, latest=None):
        quote = "Synthetic public release interval: " + earliest + " to " + (latest or earliest)
        path = self.root / (earliest + "-" + (latest or earliest) + ".txt")
        path.write_text(quote)
        return {"earliest": earliest, "latest": latest or earliest, "url": "https://example.org/paper",
                "snapshot_path": str(path), "quote": quote}

    def origin(self, status="hidden"):
        path = self.root / "exposure_manifest.txt"
        quote = "Synthetic manifest: idea-bearing conclusions are " + status + " across generation inputs, tools and memory."
        path.write_text(quote)
        self.context["source_papers"] = [{"paper_id": "O1", "title": "Synthetic origin",
            "urls": [self.source["url"]], "idea_exposure": {"status": status, "reason": "Synthetic audited exposure.",
            "snapshot_path": str(path), "quote": quote}}]

    def refresh(self):
        scope_report(self.idea, self.check, self.root)
        return self.novelty["assessment"]

    def validate(self):
        return app.validate_checks(self.result, [self.idea], require_claims=True)

    def test_all_six_facets_identical_to_hidden_origin_is_retained_rediscovery(self):
        self.origin()
        comparison = self.novelty["comparisons"][0]
        for facet in FACETS:
            comparison["facets"][facet] = copy.deepcopy(comparison["facets"]["contribution"])
        assessment = self.refresh()
        self.validate()
        self.assertEqual(assessment["task_verdict"], "INDEPENDENT_REDISCOVERY")
        self.assertTrue(assessment["candidate_retained"])
        self.assertEqual(assessment["world_novelty"], "EXISTING_MATCH")
        self.assertEqual(assessment["rediscovered_claim_ids"], ["C1"])
        self.assertEqual(self.novelty["overall_status"], "NO_COVERAGE_FOUND")

    def test_exposed_origin_is_already_known_to_agent(self):
        self.origin("exposed")
        assessment = self.refresh()
        self.validate()
        self.assertEqual(assessment["task_verdict"], "CORE_ALREADY_KNOWN")
        self.assertFalse(assessment["candidate_retained"])

    def test_unknown_exposure_cannot_be_claimed_as_independent(self):
        self.origin("unknown")
        assessment = self.refresh()
        self.validate()
        self.assertEqual(assessment["task_verdict"], "UNRESOLVED")
        self.assertTrue(assessment["candidate_retained"])

    def test_later_identical_work_does_not_defeat_historical_novelty(self):
        self.source["publication_date"] = self.date_record("2021-01-01")
        assessment = self.refresh()
        self.validate()
        self.assertEqual(assessment["source_roles"][0]["role"], "later_work")
        self.assertEqual(assessment["task_verdict"], "RETAIN_CANDIDATE")
        self.assertEqual(assessment["all_sources_status"], "COVERED")

    def test_earlier_core_coverage_disqualifies_even_with_different_facets(self):
        self.source["publication_date"] = self.date_record("2019-01-01")
        assessment = self.refresh()
        self.validate()
        self.assertEqual(assessment["task_verdict"], "CORE_ALREADY_KNOWN")

    def test_hidden_origin_does_not_exempt_other_earlier_work(self):
        self.origin()
        other = copy.deepcopy(self.source)
        other.update(source_id="P2", url="https://example.org/earlier", publication_date=self.date_record("2019-01-01"))
        self.check["prior_work"]["sources"].append(other)
        evidence = copy.deepcopy(self.novelty["evidence"][0])
        evidence.update(source_id="P2", evidence_id="E2")
        self.novelty["evidence"].append(evidence)
        comparison = copy.deepcopy(self.novelty["comparisons"][0])
        comparison["source_id"] = "P2"
        for row in [*comparison["facets"].values(), *comparison["claim_relations"]]:
            if row["evidence_ids"]:
                row["evidence_ids"] = ["E2"]
        self.novelty["comparisons"].append(comparison)
        assessment = self.refresh()
        self.validate()
        self.assertEqual(assessment["task_verdict"], "CORE_ALREADY_KNOWN")
        self.assertEqual(assessment["rediscovered_claim_ids"], ["C1"])

    def test_unknown_publication_date_is_unresolved_not_disqualifying(self):
        self.source["publication_date"] = None
        assessment = self.refresh()
        self.validate()
        self.assertEqual(assessment["task_verdict"], "UNRESOLVED")
        self.assertTrue(assessment["candidate_retained"])

    def test_same_day_without_order_is_unresolved(self):
        self.assertEqual(self.refresh()["source_roles"][0]["timing"], "overlap")
        self.validate()
        self.assertEqual(self.novelty["assessment"]["task_verdict"], "UNRESOLVED")

    def test_year_only_date_is_an_interval(self):
        self.source["publication_date"] = self.date_record("2019-01-01", "2019-12-31")
        self.assertEqual(self.refresh()["task_verdict"], "CORE_ALREADY_KNOWN")
        self.validate()

    def test_overlapping_uncertain_year_does_not_establish_prior_order(self):
        self.source["publication_date"] = self.date_record("2019-01-01", "2020-12-31")
        self.assertEqual(self.refresh()["task_verdict"], "UNRESOLVED")
        self.validate()

    def test_unknown_cutoff_prevents_confirmed_historical_rediscovery(self):
        self.origin()
        self.context["reference_date"] = None
        self.assertEqual(self.refresh()["task_verdict"], "UNRESOLVED")
        self.validate()

    def test_checker_cannot_change_frozen_exposure(self):
        self.origin("exposed")
        self.refresh()
        self.novelty["assessment"]["context"]["source_papers"][0]["idea_exposure"]["status"] = "hidden"
        with self.assertRaises(ValueError):
            self.validate()

    def test_checker_cannot_relabel_later_work_as_earlier(self):
        self.source["publication_date"] = self.date_record("2021-01-01")
        self.refresh()
        self.novelty["assessment"]["source_roles"][0]["eligible"] = True
        with self.assertRaises(ValueError):
            self.validate()

    def test_exposure_requires_a_record_not_checker_guess(self):
        self.origin()
        self.context["source_papers"][0]["idea_exposure"]["quote"] = "Invented exposure audit."
        with self.assertRaises(ValueError):
            self.refresh()

    def test_date_evidence_must_exist(self):
        self.source["publication_date"]["quote"] = "Fabricated publication date."
        with self.assertRaises(ValueError):
            self.refresh()

    def test_unknown_source_dates_must_be_explicit(self):
        self.source.pop("publication_date")
        with self.assertRaises(ValueError):
            self.refresh()

    def test_old_v1_report_reads_but_cannot_replace_new_check(self):
        result = claim_report([self.idea], self.root, known_direction=True, version=LEGACY_VERSION)
        app.validate_checks(result, [self.idea])
        with self.assertRaises(ValueError):
            app.validate_checks(result, [self.idea], require_claims=True)

    def test_current_mode_still_counts_existing_work(self):
        self.idea.pop("evaluation_context")
        self.assertEqual(self.refresh()["task_verdict"], "CORE_ALREADY_KNOWN")
        self.validate()

    def test_context_text_is_not_candidate_claim_text(self):
        self.origin()
        self.refresh()
        self.novelty["claims"][0]["idea_quote"] = "Synthetic origin"
        with self.assertRaises(ValueError):
            self.validate()

    def test_multiple_origin_papers_can_be_hidden_with_one_explicit_reference(self):
        self.origin()
        second = copy.deepcopy(self.context["source_papers"][0])
        second.update(paper_id="O2", title="Second origin", urls=["https://example.org/second"])
        self.context["source_papers"].append(second)
        self.assertEqual(self.refresh()["task_verdict"], "INDEPENDENT_REDISCOVERY")
        self.validate()

    def test_unlisted_origin_url_cannot_be_exempted_by_title(self):
        self.origin()
        self.context["source_papers"][0]["urls"] = ["https://example.org/different"]
        self.source["publication_date"] = self.date_record("2019-01-01")
        self.assertEqual(self.refresh()["task_verdict"], "CORE_ALREADY_KNOWN")
        self.validate()

    def test_cli_context_is_checker_only_and_round_trips(self):
        self.origin()
        context_path = self.root / "context.json"
        context_path.write_text(json.dumps({"I1": self.context}))
        brief = self.root / "brief.md"
        brief.write_text("Propose an idea from observations.")
        generated = {k: v for k, v in self.idea.items() if k != "evaluation_context"}
        run = self.root / "run"

        def fake_stage(run_dir, stage_id, role, prompt, inputs, model, effort, timeout):
            if stage_id == "propose":
                self.assertNotIn(context_path, inputs)
                return brief, {"ideas": [generated]}
            ideas = app.read(inputs[0])["ideas"]
            self.assertEqual(ideas[0]["evaluation_context"], self.context)
            return brief, claim_report(ideas, run_dir / "fixture", known_direction=True)

        argv = ["idea_check.py", "--brief", str(brief), "--run-dir", str(run), "--count", "1",
                "--evaluation-context", str(context_path)]
        with patch.object(sys, "argv", argv), patch.object(app, "stage_run", side_effect=fake_stage), patch("builtins.print"):
            app.main()
        report = app.read(run / "check_report.json")
        self.assertEqual(report["checks"][0]["novelty"]["assessment"]["task_verdict"], "INDEPENDENT_REDISCOVERY")


if __name__ == "__main__":
    unittest.main()
