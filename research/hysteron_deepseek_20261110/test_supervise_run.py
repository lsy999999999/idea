import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('supervisor', Path(__file__).with_name('supervise_run.py'))
supervisor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supervisor)


class RecoveryTests(unittest.TestCase):
    def run_scenario(self, error, resume=True):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            failure = root / 'LAST_FAILURE.json'
            final = root / 'final.json'
            failure.write_text(json.dumps({'error': error}))
            (root / 'model_config.json').write_text(json.dumps({'model': 'deepseek-flash', 'reasoning_effort': 'high', 'max_completion_tokens': 32768}))
            truncated = root / '169.response.json'
            truncated.write_text('preserved incomplete response')
            def finish(*args, **kwargs):
                final.write_text(json.dumps({'status': 'complete'}))
                return SimpleNamespace(returncode=0)
            with patch.multiple(supervisor, ROOT=root, LOCK=root/'.run.lock', FAILURE=failure,
                                FINAL=final, EVENTS=root/'events.jsonl', RUN=root/'run.py'), \
                 patch.object(supervisor.subprocess, 'run', side_effect=finish) as run:
                result = supervisor.main(resume)
            return result, run.call_count, json.loads((root/'model_config.json').read_text()), truncated.read_text()

    def test_existing_truncation_resumes_without_overwriting_response(self):
        result, calls, cfg, original = self.run_scenario('Model response truncated; no partial result accepted')
        self.assertEqual((result, calls), (0, 1))
        self.assertEqual(cfg['max_completion_tokens'], 65536)
        self.assertEqual((cfg['model'], cfg['reasoning_effort']), ('deepseek-flash', 'high'))
        self.assertEqual(original, 'preserved incomplete response')

    def test_scientific_validation_error_does_not_trigger_automatic_rewrite(self):
        result, calls, cfg, _ = self.run_scenario('Source identity mismatch')
        self.assertEqual((result, calls), (1, 0))
        self.assertEqual(cfg['max_completion_tokens'], 32768)

    def test_stale_failure_is_not_restarted_without_explicit_resume(self):
        result, calls, _, _ = self.run_scenario('BUDGET_EXHAUSTED', resume=False)
        self.assertEqual((result, calls), (1, 0))


if __name__ == '__main__':
    unittest.main()
