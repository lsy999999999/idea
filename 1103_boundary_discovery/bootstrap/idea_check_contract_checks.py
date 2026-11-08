"""Local checks of the idea-first handoff; no model or scientific validation."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import idea_check as flow
from novelty_fixtures import claim_report


class IdeaCheckContracts(unittest.TestCase):
    def setUp(self):
        # A conceptual direction with no equation, proof, implementation or data.
        self.ideas = [{"id": "I1", "title": "待研究方向", "idea": "探索新的状态表示。"}]
        self.result = {
            "searches": [{"query": "example query", "url": "https://example.org/search",
                          "status": "completed", "idea_ids": ["I1"]}],
            "checks": [{"idea_id": "I1", "prior_work": {
                "verdict": "no_close_work_found", "reason": "暂未找到相近工作。", "sources": []},
                "math": {"verdict": "no_obvious_error", "reason": "方向大体可行。", "errors": []}}]}

    def test_unsolved_conceptual_direction_is_retained(self):
        flow.validate_ideas({"ideas": self.ideas})
        flow.validate_checks(self.result, self.ideas)

    def test_similar_work_and_math_pass_are_independent(self):
        prior = self.result["checks"][0]["prior_work"]
        prior.update(verdict="already_done", sources=[{
            "title": "Example fixture", "url": "https://example.org/paper",
            "accessed_on": "2026-11-04", "content_note": "核心方向相近，细节不同。",
            "similarity": "very_similar"}])
        flow.validate_checks(self.result, self.ideas)
        self.assertEqual(self.result["checks"][0]["math"]["verdict"], "no_obvious_error")
        prior["sources"] = []
        with self.assertRaises(ValueError):
            flow.validate_checks(self.result, self.ideas)

    def test_failed_retrieval_stays_unclear(self):
        self.result["searches"][0]["status"] = "failed"
        with self.assertRaises(ValueError):
            flow.validate_checks(self.result, self.ideas)
        self.result["checks"][0]["prior_work"]["verdict"] = "unclear"
        flow.validate_checks(self.result, self.ideas)

    def test_search_for_one_idea_cannot_cover_another(self):
        second = {**self.ideas[0], "id": "I2"}
        check = copy.deepcopy(self.result["checks"][0])
        check["idea_id"] = "I2"
        self.result["checks"].append(check)
        with self.assertRaises(ValueError):
            flow.validate_checks(self.result, [*self.ideas, second])

    def test_no_candidate_can_be_silently_omitted(self):
        with self.assertRaises(ValueError):
            flow.validate_checks(self.result, [*self.ideas, {**self.ideas[0], "id": "I2"}])

    def test_math_error_must_identify_a_concrete_claim(self):
        math = self.result["checks"][0]["math"]
        math["verdict"] = "obvious_error"
        with self.assertRaises(ValueError):
            flow.validate_checks(self.result, self.ideas)
        math["errors"] = [{"claim": "1 + 1 = 3", "explanation": "整数加法结果应为 2。"}]
        flow.validate_checks(self.result, self.ideas)

    def test_pipeline_calls_only_builder_then_checker(self):
        with tempfile.TemporaryDirectory(dir=flow.PROJECT / "bootstrap") as tmp:
            root = Path(tmp)
            brief = root / "brief.md"
            brief.write_text("构建新的研究 idea。")
            run = root / "run"
            def fake_stage(run, stage_id, role, prompt, inputs, model, effort, timeout):
                if stage_id == "propose":
                    return brief, {"ideas": self.ideas}
                # The checker sees an explicit candidate file from the prior handoff.
                self.assertEqual(flow.read(inputs[0])["ideas"], self.ideas)
                self.result = claim_report(self.ideas, run / "synthetic_evidence")
                return brief, self.result
            argv = ["idea_check.py", "--brief", str(brief), "--run-dir", str(run), "--count", "1"]
            with patch.object(sys, "argv", argv), patch.object(flow, "stage_run", side_effect=fake_stage) as call:
                flow.main()
            self.assertEqual([c.args[2] for c in call.call_args_list], ["idea_builder", "idea_check_agent"])
            self.assertEqual(flow.read(run / "ideas.json")["ideas"], self.ideas)
            self.assertEqual(flow.read(run / "check_report.json")["checks"], self.result["checks"])


if __name__ == "__main__":
    unittest.main()
