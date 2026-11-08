"""One-scenario adapter to the existing general persistent-learning runner.

Scientific prompts, stages, memory implementation and checker are unchanged.
The fish-specific temporal/measurement adapter is not used for this table dataset.
"""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT / 'src'))
import learning_lab as lab
from learning_memory import Memory

p = argparse.ArgumentParser()
p.add_argument('--executor', choices=['queue', 'cli'], default='queue')
a = p.parse_args()
lab.CASES['wine'] = [
    ('wine_chemist_eval', '葡萄酒化学、感官测量与酿造过程'),
    ('measurement_theorist_eval', '统计物理、测量理论与可辨识性'),
]
scenario = PROJECT / 'learning_lab/scenarios/wine.md'
text = (ROOT / 'SCENARIO.md').read_text()
if scenario.exists() and scenario.read_text() != text:
    raise ValueError('Scenario already exists with different content')
if not scenario.exists():
    scenario.write_text(text)
run = PROJECT / 'runs/e2e_eval_20261106_wine'
# Queue entry expects a manifest normally created by the CLI runner.
# Initialize it after the unmodified runner creates its new run directory.
original_write = lab.write
def write_with_queue_manifest(path, value):
    original_write(path, value)
    if Path(path) == run / 'learning_state.json' and not (run / 'manifest.json').exists():
        original_write(run / 'manifest.json', {'stages': {}})
lab.write = write_with_queue_manifest
args = SimpleNamespace(model='gpt-6-luna', effort='low', timeout=300,
                       check_timeout=600, executor=a.executor)
lab.run_case('wine', run, args, Memory(ROOT / 'researchers'))
