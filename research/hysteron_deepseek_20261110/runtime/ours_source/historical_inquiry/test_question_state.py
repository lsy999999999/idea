"""State/provenance regression tests; model calls are mocked, not research evidence."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from prepare import HERE, save
from question_state import QuestionState, file_hash
from run import Pilot, RESEARCHERS


def decision(view, action="retain", question=None, influences=None):
    return {"base": copy.deepcopy(view["ref"]) if view else None,
            "action": action, "question": question if question is not None else view["question"],
            "reason": "A recorded decision with an explicit reason.",
            "influenced_by": influences or []}


class QuestionStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = QuestionState(self.root / "questions", ["A", "B"])
        self.initial_hashes = {}
        for rid in ("A", "B"):
            result = {"initial_question": "Independent question " + rid}
            path = self.root / ("initial_" + rid + ".json")
            save(path, result)
            self.store.accept("initial_" + rid, rid, result, path, initial=True)
            self.initial_hashes[path] = file_hash(path)

    def accept(self, stage, rid, packet, personal=None, shared=None):
        result = {"personal_question_update": personal or decision(packet["self"]),
                  "shared_question_update": shared}
        path = self.root / (stage + ".json")
        save(path, result)
        return self.store.accept(stage, rid, result, path, packet)

    def propose_shared(self):
        packet = self.store.packet("exchange_A", "A")
        self.accept("exchange_A", "A", packet, shared=decision(None, "propose", "Shared question"))

    def test_shared_proposal_leaves_both_personal_questions_intact(self):
        self.propose_shared()
        packet = self.store.packet("exchange_B", "B")
        self.assertEqual(packet["self"]["question"], "Independent question B")
        self.assertEqual(packet["self"]["ref"]["owner"], "B")
        self.assertEqual(packet["peer_questions"][0]["question"], "Independent question A")
        self.assertEqual(packet["shared_question"]["question"], "Shared question")
        self.assertEqual(packet["shared_question"]["proposed_by"], "A")

    def test_peer_reference_cannot_overwrite_personal_state(self):
        packet = self.store.packet("bad_owner", "B")
        update = decision(packet["peer_questions"][0], "revise", "Copied peer question")
        before = self.store.current()
        with self.assertRaisesRegex(ValueError, "wrong owner"):
            self.accept("bad_owner", "B", packet, personal=update)
        self.assertEqual(self.store.current(), before)

    def test_explicit_adoption_records_real_before_state_and_preserves_history(self):
        self.propose_shared()
        packet = self.store.packet("adopt_B", "B")
        update = decision(packet["self"], "revise", packet["shared_question"]["question"],
                          [packet["shared_question"]["ref"]])
        event = self.accept("adopt_B", "B", packet, personal=update)
        self.assertEqual(event["before"]["self"]["question"], "Independent question B")
        self.assertEqual(self.store.current()["personal"]["B"]["version"], 2)
        self.assertEqual(self.store.current()["personal"]["A"]["version"], 1)
        self.assertEqual(event["updates"][0]["influenced_by"], [packet["shared_question"]["ref"]])
        for path, expected in self.initial_hashes.items():
            self.assertEqual(file_hash(path), expected)

    def test_retain_cannot_silently_change_question(self):
        packet = self.store.packet("bad_retain", "B")
        with self.assertRaisesRegex(ValueError, "Retain cannot"):
            self.accept("bad_retain", "B", packet,
                        personal=decision(packet["self"], "retain", "A different question"))

    def test_shared_change_cannot_be_lost_to_a_stale_reply(self):
        self.propose_shared()
        stale = self.store.packet("stale_B", "B")
        latest = self.store.packet("new_A", "A")
        self.accept("new_A", "A", latest,
                    shared=decision(latest["shared_question"], "revise", "Shared version two"))
        with self.assertRaisesRegex(ValueError, "stale version"):
            self.accept("stale_B", "B", stale,
                        shared=decision(stale["shared_question"], "revise", "Lost update"))
        self.assertEqual(self.store.current()["shared"]["question"], "Shared version two")

    def test_missing_change_reason_is_rejected(self):
        packet = self.store.packet("missing_reason", "A")
        update = decision(packet["self"], "revise", "New question")
        update["reason"] = ""
        with self.assertRaisesRegex(ValueError, "reason"):
            self.accept("missing_reason", "A", packet, personal=update)

    def test_packet_freezes_the_state_the_call_saw(self):
        self.propose_shared()
        packet = self.store.packet("frozen_B", "B")
        latest = self.store.packet("advance_A", "A")
        self.accept("advance_A", "A", latest,
                    shared=decision(latest["shared_question"], "revise", "Later shared question"))
        self.assertEqual(self.store.packet("frozen_B", "B"), packet)
        self.assertEqual(self.store.packet("next_B", "B")["shared_question"]["question"], "Later shared question")

    def test_ambiguous_before_fields_are_rejected(self):
        packet = self.store.packet("ambiguous", "B")
        result = {"question_before": "I was actually asking A's question",
                  "personal_question_update": decision(packet["self"]), "shared_question_update": None}
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            self.store.validate("ambiguous", "B", result, packet)

    def test_restart_and_duplicate_commit_preserve_question_versions(self):
        packet = self.store.packet("retain_A", "A")
        event = self.accept("retain_A", "A", packet)
        restarted = QuestionState(self.store.root, ["A", "B"])
        path = Path(event["source_result"])
        restarted.accept("retain_A", "A", json.loads(path.read_text()), path, packet)
        self.assertEqual(len(restarted.events()), 3)
        self.assertEqual(restarted.current(), self.store.current())


class PipelineQuestionStateTests(unittest.TestCase):
    def test_controller_passes_owned_state_and_keeps_legacy_run_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "test_case"
            for subdir in ("allowed", "controller_only"):
                shutil.copytree(HERE / "cases/airfoil_001" / subdir, case / subdir)
            legacy = case / "run/frozen.txt"
            legacy.parent.mkdir()
            legacy.write_text("Existing scientific run stays frozen.")
            save(case / "controller_only/protected_hashes.json", {str(legacy): file_hash(legacy)})
            seen = {}

            def fake_invoke(prompt, attempt, timeout):
                sid = Path(attempt).parent.name
                context = json.loads(prompt.split("INPUTS:\n", 1)[1])
                seen[sid] = context
                r = {"summary": "Mocked controller regression, not a live scientific finding.",
                     "artifacts": [], "evidence": [], "claims": [], "limitations": [], "next_actions": [],
                     "evidence_claims": [], "doubts": []}
                researcher = context.get("researcher")
                if sid.startswith("01_initial_"):
                    r["initial_question"] = "Personal question of " + researcher
                elif researcher:
                    state = context["question_state"]
                    r["personal_question_update"] = decision(state["self"])
                    r["shared_question_update"] = (decision(None, "propose", "A separate shared question")
                                                   if sid == "02_exchange_0" else None)
                if sid.startswith("02_exchange_"):
                    r["learning_request"] = {"needed": sid.endswith("_0"), "gap": "A specific test gap",
                                             "source_ids": ["F1"], "spectrum_ids": [0], "all_rows": False}
                if sid.startswith(("01_initial_", "03_learn_", "04_return_")):
                    r["memory_notes"] = [{"key": "fixture_concept", "title": "Mock concept", "kind": "interpretation",
                        "mastery": "read", "understanding": "Only fixture content", "conditions": "Only in this test",
                        "example": "A fixture", "open_questions": "A test question", "tags": ["flow"],
                        "sources": ["data.csv"], "revision_reason": "Fixture revision"}]
                if sid == "05_candidates":
                    r["ideas"] = []
                if sid == "06_check":
                    r["checks"] = []
                return r

            with patch("run.invoke", side_effect=fake_invoke):
                pilot = Pilot(case, 30)
                pilot.execute()
            self.assertEqual(legacy.read_text(), "Existing scientific run stays frozen.")
            self.assertFalse((case / "run/state.json").exists())
            self.assertNotIn("question_state", seen["01_initial_1"])
            self.assertNotIn("initial", seen["01_initial_1"])  # Independent initial questions.
            rid_b = RESEARCHERS[1][0]
            packet_b = seen["02_exchange_1"]["question_state"]
            self.assertEqual(packet_b["self"]["question"], "Personal question of " + rid_b)
            self.assertEqual(packet_b["shared_question"]["question"], "A separate shared question")
            self.assertEqual(seen["02_exchange_1"]["initial"][0]["researcher"], RESEARCHERS[0][0])
            for sid in ("03_learn_0", "04_return_0", "04_return_1", "07_fresh_continuation"):
                self.assertIn("question_state", seen[sid])
            before = pilot.questions.current()
            with patch("run.invoke", side_effect=AssertionError("Completed stages must not call a model")):
                Pilot(case, 30).execute()
            self.assertEqual(Pilot(case, 30).questions.current(), before)


if __name__ == "__main__":
    unittest.main()
