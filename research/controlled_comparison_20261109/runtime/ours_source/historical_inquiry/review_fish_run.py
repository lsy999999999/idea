"""Post-run descriptive audit. Does not call actors or modify frozen artifacts."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from fish_materials import CASE, digest
from prepare import save


def read(path):
    return json.loads(Path(path).read_text())


def review(run):
    run = Path(run)
    state = read(run/'state.json')
    if state.get('status') != 'complete':
        raise ValueError('Review requires a completed frozen run')
    stages = {sid: read(run/'stages'/sid/'result.json') for sid in state['stages']}
    events = sorted([read(p) for p in (run/'question_state/events').glob('*.json')], key=lambda x: x['sequence'])
    claims = {c['ref']: c for p in (run/'internal_verification/events').glob('*.json') for c in read(p)['claims']}
    reports = [read(p) for p in (run/'internal_verification/reports').glob('*.json')]
    checked = {f['claim_ref'] for r in reports for f in r['findings']}
    snapshots = [read(p) for p in (run/'memory_retrieval').glob('*.json')]
    indexes = {p.parent.name: read(p) for p in (run.parent.parent/'researchers').glob('*/index.json')}
    attempts = [read(p) for p in (run/'stages').glob('*/attempt-*/execution_audit.json')]
    requests = {sid: s['learning_request'] for sid, s in stages.items() if 'learning_request' in s}
    ideas = read(run/'ideas.json')['ideas']
    freeze = read(run/'GENERATION_FREEZE.json')
    output = {
        'logical_stages': len(stages), 'successful_raw_attempts': len(attempts),
        'token_usage': {k: sum(u.get(k, 0) for a in attempts for u in a.get('usage', []))
                        for k in ('input_tokens', 'cached_input_tokens', 'output_tokens')},
        'learning_requests': requests,
        'requested_learning_count': sum(r['needed'] for r in requests.values()),
        'broker_replies': len(list((run/'broker').glob('*.json'))),
        'current_notes': sum(len(i['notes']) for i in indexes.values()),
        'note_versions': len(list((run.parent.parent/'researchers').glob('*/notes/*/v*.json'))),
        'retrieval_count': len(snapshots),
        'retrievals_with_notes': sum(bool(s['retrieved']) for s in snapshots),
        'fresh_session_retrieval': read(run/'memory_retrieval/04_fresh_continuation.json'),
        'question_changes': [{'stage': e['stage'], 'researcher': e['researcher'],
                              'updates': e['updates'], 'decisions': e.get('decisions', {})} for e in events],
        'evidence_claims': len(claims), 'verification_batches': len(reports),
        'verified_claims': [f for r in reports for f in r['findings']],
        'unchecked_consequential_refs': [r for r,c in claims.items()
            if c['kind'] != 'hypothesis' and c['use'] == 'research_decision' and r not in checked],
        'candidate_claim_ref_errors': {i['id']: [r for r in i.get('supporting_claim_refs', []) if r not in claims]
                                      for i in ideas},
        'generation_freeze_intact': all(digest(p) == h for p,h in freeze['files'].items()),
        'status': 'descriptive_review_not_scientific_validation',
    }
    save(run/'review/PROCESS_REVIEW.json', output)
    print(json.dumps({k:v for k,v in output.items() if k not in {
        'learning_requests', 'fresh_session_retrieval', 'question_changes', 'verified_claims'}}, ensure_ascii=False, indent=2))
    return output


if __name__ == '__main__':
    review(Path(sys.argv[1]) if len(sys.argv) > 1 else CASE/'runs/inquiry_001')
