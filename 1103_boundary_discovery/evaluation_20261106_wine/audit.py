"""Audit actual saved artifacts of this single-scene execution."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
RUN = PROJECT / 'runs/e2e_eval_20261106_wine'
def load(p):
    return json.loads(p.read_text())
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

state = load(RUN / 'learning_state.json')
before = load(ROOT / 'SOURCE_HASHES_BEFORE.json')
changed_sources = [p for p, h in before.items() if sha(Path(p)) != h]
stages = []
for sid, record in state['stages'].items():
    p = Path(record['path'])
    result = load(p)
    stages.append({'stage': sid, 'path': str(p),
        'hash_matches': sha(p) == record['sha256'],
        'adapter': record.get('adapter', 'cli'),
        'agent': record.get('agent_name'),
        'summary': result['summary'],
        'memory_use': result.get('memory_use', []),
        'learning_change': result.get('learning_change'),
        'changed_because': result.get('changed_because')})
notes = list((ROOT / 'researchers').glob('*/notes/*/v*.json'))
bad_notes = []
for p in notes:
    n = load(p)
    if sha(Path(n['source_result'])) != n['source_sha256']:
        bad_notes.append(str(p))
delivery = ROOT / 'SUPPLEMENTAL_INPUT_DELIVERY.json'
changed_supplemental = []
if delivery.exists():
    changed_supplemental = [p for p, h in load(delivery)['files'].items()
                           if sha(Path(p)) != h]
indices = list((ROOT / 'researchers').glob('*/index.json'))
current_notes = sum(len(load(p)['notes']) for p in indices)
baseline = load(ROOT / 'BASELINE_ORIGINALS.json')
changed_baseline = [item['source']
                    for section in ('final_records', 'initial_records')
                    for item in baseline[section]
                    if sha(Path(item['source'])) != item['source_sha256']]
frozen = RUN / 'COMPARISON_GENERATION_FREEZE.json'
changed_frozen = []
if frozen.exists():
    changed_frozen = [p for p, h in load(frozen)['files'].items()
                      if not Path(p).exists() or sha(Path(p)) != h]
result = {'state': state['status'], 'logical_stages': len(stages),
          'stages': stages, 'source_changes': changed_sources,
          'memory_versions': len(notes), 'bad_memory_provenance': bad_notes,
          'current_memory_notes': current_notes,
          'changed_supplemental_inputs': changed_supplemental,
          'changed_historical_comparison_files': changed_baseline,
          'changed_frozen_generation': changed_frozen,
          'requested_model': 'gpt-6-luna', 'requested_effort': 'low',
          'one_click_cli_completed': False,
          'pending_stage': load(RUN / 'PENDING_NATIVE.json')['stage']
              if (RUN / 'PENDING_NATIVE.json').exists() else None}
(ROOT / 'AUDIT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps({k:v for k,v in result.items() if k != 'stages'},ensure_ascii=False))
if changed_sources or bad_notes or changed_frozen or changed_supplemental or changed_baseline:
    raise SystemExit(1)
