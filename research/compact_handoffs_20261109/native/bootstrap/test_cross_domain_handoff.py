"""Offline handoff test: all proposals reach the two-part checker unchanged."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
import cross_domain_ideas as app
from novelty_fixtures import claim_report


class Handoff(unittest.TestCase):
    def test_structured_assumptions_are_retained(self):
        card = {"domain": "Physics", "structures": [{"name": "x", "relation": "y", "assumptions": ["a", "b"],
            "sources": [{"title": "Fixture", "url": "https://example.org", "accessed_on": "2026-11-04", "content_note": "fixture"}]}],
            "open_tensions": ["open"]}
        self.assertEqual(app.validate_card({"domain_card": card}, "Physics"), card)

    def test_all_ideas_reach_final_checker_and_completed_resume_is_read_only(self):
        with tempfile.TemporaryDirectory(dir=PROJECT / "bootstrap") as folder:
            root = Path(folder)
            brief = root / "brief.md"; brief.write_text("Propose cross-field research ideas.")
            domains = root / "domains.json"; domains.write_text(json.dumps(["Ecology", "Physics"]))
            run = root / "run"
            proposed = [{"id": "I1", "title": "An unresolved idea", "idea": "A deliberately unsolved proposal.",
                "domains": ["Ecology", "Physics"], "research_question": "What state is missing?",
                "conceptual_move": "Transfer an organizing principle", "why_this_crossing_matters": "Changes the proposed state",
                "concept_mapping": [{"source_concept": str(i), "target_counterpart": str(i), "transfer": "relation",
                                     "where_analogy_may_break": "assumptions"} for i in range(2)]}]
            calls = []

            def fake(run_dir, stage, role, prompt, inputs, model, effort, timeout):
                calls.append(role)
                result = {"summary": "fake", "artifacts": [], "evidence": [], "claims": [], "limitations": [], "next_actions": []}
                if role == "disciplinary_input":
                    domain = "Ecology" if stage == "domain_00" else "Physics"
                    result["domain_card"] = {"domain": domain, "structures": [{"name": "structure", "relation": "relation",
                        "assumptions": "assumption", "sources": [{"title": "Offline fixture", "url": "https://example.org/source",
                        "accessed_on": "2026-11-04", "content_note": "Not actual scientific evidence"}]}], "open_tensions": ["unsolved"]}
                elif role == "cross_disciplinary_idea_builder":
                    self.assertEqual(len([p for p in inputs if p.name == 'result.json']), 2)
                    result["ideas"] = copy.deepcopy(proposed)
                else:
                    self.assertEqual(role, "idea_check_agent")
                    packet = json.loads(next(p for p in inputs if p.name == "ideas.json").read_text())
                    self.assertEqual(packet["ideas"], proposed)
                    result.update(claim_report(proposed, run_dir / "stages" / stage / "synthetic_evidence", known_direction=True))
                file = run_dir / "stages" / stage / "result.json"; file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(json.dumps(result)); return file, result

            argv = ["cross_domain_ideas", "--brief", str(brief), "--domains", str(domains), "--run-dir", str(run), "--count", "1"]
            with patch.object(app, "stage_run", fake), patch.object(sys, "argv", argv), patch("builtins.print"):
                app.main()
                self.assertEqual(calls, ["disciplinary_input", "disciplinary_input", "cross_disciplinary_idea_builder", "idea_check_agent"])
                app.main()
                self.assertEqual(len(calls), 4)
            self.assertEqual(json.loads((run / "ideas.json").read_text())["ideas"], proposed)
            checks = json.loads((run / "check_report.json").read_text())["checks"]
            self.assertEqual(checks[0]["prior_work"]["verdict"], "close_direction_found")
            self.assertEqual(checks[0]["math"]["verdict"], "no_obvious_error")

    def test_field_names_without_correspondences_are_incomplete_generation(self):
        result = {"ideas": [{"id": "I1", "title": "title", "idea": "idea", "domains": ["Ecology", "Physics"],
            "research_question": "question", "conceptual_move": "move", "why_this_crossing_matters": "why", "concept_mapping": []}]}
        with self.assertRaises(ValueError):
            app.validate_bridges(result, 1, ["Ecology", "Physics"])


if __name__ == "__main__":
    unittest.main()
