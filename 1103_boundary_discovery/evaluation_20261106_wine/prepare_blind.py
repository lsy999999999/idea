"""Mask provenance for an auxiliary text-quality comparison, not a novelty test."""
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / 'BASELINE_ORIGINALS.json').read_text())
# One original, fully specified proposal for each of the seven PDF wine themes.
selected = [('old_A_1', 'I1'), ('old_A_2', 'I2'), ('old_B_2', 'I1'),
            ('old_B_3', 'I3'), ('old_B_3', 'I1'), ('old_A_3', 'I2'),
            ('old_C_2', 'I1')]
cards = []
for record_id, idea_id in selected:
    record = next(x for x in data['initial_records'] if x['id'] == record_id)
    candidate = next(c for c in record['content']['candidates'] if c['id'] == idea_id)
    # Remove orchestration/quality self-ratings; retain all scientific content verbatim.
    omit = {'id', 'history_match', 'history_relation', 'discriminating_delta',
            'quality_gate', 'next_action'}
    cards.append((record_id + '/' + idea_id, {k:v for k,v in candidate.items() if k not in omit}))
new = json.loads((ROOT.parent / 'runs/e2e_eval_20261106_wine/ideas.json').read_text())
for idea in new['ideas']:
    cards.append(('new/' + idea['id'], {k:v for k,v in idea.items()
                 if k not in {'id', 'emergence', 'domains', 'evaluation_context'}}))
random.Random(11062026).shuffle(cards)
masked = [{'id':f'T{i+1:02d}', 'text': card} for i, (_,card) in enumerate(cards)]
key = {f'T{i+1:02d}': origin for i, (origin,_) in enumerate(cards)}
(ROOT / 'BLIND_CARDS.json').write_text(json.dumps(masked, ensure_ascii=False, indent=2))
(ROOT / 'BLIND_KEY_CONTROLLER_ONLY.json').write_text(json.dumps(key, indent=2))
print(len(masked))
