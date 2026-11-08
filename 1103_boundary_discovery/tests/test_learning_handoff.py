import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discover import PROJECT, read, write
from learning_memory import digest
from import_learning_handoff import main


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=PROJECT / "tests")
        self.root = Path(self.temp.name)
        self.run = self.root / "run"
        self.workspace = self.run / "stages" / "test" / "workspace"
        self.workspace.mkdir(parents=True)
        self.input = self.root / "input.md"
        self.input.write_text("original evidence")
        self.request = {"stage": "test", "workspace": str(self.workspace), "model": "test-model",
            "effort": "low", "input_hashes": [{"path": str(self.input), "sha256": digest(self.input)}]}
        write(self.run / "PENDING_NATIVE.json", self.request)
        write(self.run / "learning_state.json", {"stages": {}})
        write(self.run / "manifest.json", {"stages": {}})
        write(self.workspace / "result.json", {"summary": "Test fixture only", "artifacts": ["result.json"],
            "evidence": [], "claims": [], "limitations": [], "next_actions": []})

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self):
        with patch.object(sys, "argv", ["import", "--run", str(self.run), "--agent", "test-agent"]):
            main()

    def test_admission_preserves_output_and_adapter(self):
        original = (self.workspace / "result.json").read_bytes()
        self.invoke()
        self.assertEqual((self.workspace / "result.json").read_bytes(), original)
        self.assertEqual(read(self.run / "manifest.json")["stages"]["test"]["execution_adapter"], "collaboration")
        self.assertTrue((self.run / "native_dispatch/test.json").exists())
        self.assertFalse((self.run / "PENDING_NATIVE.json").exists())

    def test_changed_input_cannot_enter_completed_state(self):
        self.input.write_text("changed evidence")
        with self.assertRaisesRegex(AssertionError, "Input mutated"):
            self.invoke()
        self.assertEqual(read(self.run / "learning_state.json")["stages"], {})

    def test_wrong_run_workspace_rejected(self):
        self.request["workspace"] = str(self.root)
        write(self.run / "PENDING_NATIVE.json", self.request)
        with self.assertRaisesRegex(AssertionError, "belong to this run"):
            self.invoke()


if __name__ == "__main__":
    unittest.main()
