import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from learning_memory import Memory
from discover import write, read


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.memory = Memory(self.root / "researchers")
        self.memory.identity("physicist", "physics")

    def tearDown(self):
        self.temp.cleanup()

    def result(self, filename, **updates):
        note = {"key": "hidden_state", "title": "State and observation", "kind": "interpretation",
            "mastery": "used", "understanding": "Equal observations need not imply equal states.",
            "conditions": "Observation map is many to one", "example": "(1,0) and (0,1) both sum to 1",
            "open_questions": "Which perturbation distinguishes them?", "tags": ["state", "memory"], "sources": []}
        note.update(updates)
        path = self.root / filename
        write(path, {"memory_notes": [note]})
        return path

    def test_revision_retains_old_and_retrieves_current(self):
        first = self.result("one.json")
        self.memory.commit("physicist", "task_A", "learn", first)
        second = self.result("two.json", kind="correction", understanding="Only dynamically relevant hidden differences matter.",
                             revision_reason="Original statement omitted future relevance")
        self.memory.commit("physicist", "task_B", "learn", second)
        packet = self.memory.retrieve("physicist", "state memory")
        current = packet["retrieved"][0]["note"]
        self.assertEqual(current["version"], 2)
        self.assertEqual(current["source_task"], "task_B")
        self.assertEqual(read(current["supersedes"])["version"], 1)

    def test_idempotent_commit_and_changed_source_rejected(self):
        source = self.result("one.json")
        self.memory.commit("physicist", "task_A", "learn", source)
        self.memory.commit("physicist", "task_A", "learn", source)
        self.assertEqual(self.memory.index("physicist")["notes"]["hidden_state"]["version"], 1)
        source.write_text(source.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "source mutated"):
            self.memory.commit("physicist", "task_A", "learn", source)

    def test_invalid_revision_leaves_index_intact(self):
        self.memory.commit("physicist", "A", "learn", self.result("one.json"))
        before = self.memory.index("physicist")
        with self.assertRaisesRegex(ValueError, "requires reason"):
            self.memory.commit("physicist", "B", "learn", self.result("two.json"))
        self.assertEqual(self.memory.index("physicist"), before)

    def test_tampering_rejected(self):
        self.memory.commit("physicist", "A", "learn", self.result("one.json"))
        path = Path(self.memory.index("physicist")["notes"]["hidden_state"]["path"])
        path.write_text(path.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.memory.retrieve("physicist", "state")

    def test_irrelevant_query_returns_no_notes(self):
        self.memory.commit("physicist", "A", "learn", self.result("one.json"))
        self.assertEqual(self.memory.retrieve("physicist", "photosynthesis")['retrieved'], [])

    def test_source_knowledge_requires_source(self):
        with self.assertRaisesRegex(ValueError, "requires provenance"):
            self.memory.commit("physicist", "A", "learn", self.result("one.json", kind="source_knowledge"))

    def test_identity_cannot_silently_change(self):
        with self.assertRaises(ValueError):
            self.memory.identity("physicist", "immunology")

    def test_question_list_is_preserved_without_rewriting_model_output(self):
        path = self.result("one.json", open_questions=["Which state?", "Which observation?"])
        original = path.read_bytes()
        self.memory.commit("physicist", "A", "learn", path)
        note = self.memory.retrieve("physicist", "state")["retrieved"][0]["note"]
        self.assertEqual(note["open_questions"], ["Which state?", "Which observation?"])
        self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
