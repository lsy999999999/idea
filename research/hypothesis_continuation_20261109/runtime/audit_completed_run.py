"""Read-only integrity audit of generation and retained continuation history."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'runtime/ours_source/runs/hypothesis_metadata_optical_generation'

def read(path):
    return json.loads(path.read_text())

def verify(records):
    failures = []
    for name, expected in records.items():
        path = Path(name)
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != expected:
            failures.append({'path': name, 'expected': expected, 'actual': actual})
    return {'checked': len(records), 'unchanged': len(records) - len(failures), 'failures': failures}

def main():
    frozen = read(GEN / 'GENERATION_FREEZE.json')
    audits = {
        'frozen_generation': verify(frozen['files']),
        'frozen_research_memory': verify(frozen['memory_files']),
    }
    for name in ['CONTINUATION_MANIFEST.json', 'FLEXIBLE_CONTINUATION.json',
                 'REFERENCE_CONTINUATION.json', 'METADATA_CONTINUATION.json']:
        manifest = read(ROOT / name)
        audits[name] = verify(manifest.get('parent_files', manifest.get('preserved_parent_files')))
    stages = sorted(p.parent.parent.parent.name
                    for p in (GEN / 'stages').glob('*/api_v2/workspace/result.json'))
    inherited = [read(p) for p in (GEN / 'stages').glob('*/api_v2/workspace/INHERITANCE.json')]
    inherited_hashes = verify({row['source']: row['source_sha256'] for row in inherited})
    audits['inherited_author_outputs'] = inherited_hashes
    final_freeze = ROOT / 'runs/optical/ours/evaluation/FINAL_FREEZE.json'
    if final_freeze.exists():
        audits['frozen_evaluation'] = verify(read(final_freeze)['files'])
    result = {
        'integrity': audits,
        'all_recorded_hashes_unchanged': all(not a['failures'] for a in audits.values()),
        'completed_stage_count': len(stages), 'completed_stages': stages,
        'candidate_count': len(read(GEN / 'ideas.json')['ideas']),
        'continuation_mode': read(GEN / 'CONTINUATION_SCOPE.json')['mode'],
        'internal_review_findings': read(GEN / 'internal_review/report.json')['findings'],
        'external_evaluation_not_research_feedback': True,
        'scientific_novelty_established': False,
        'upstream_worktree_synchronized': False,
        'inherited_stage_count': len(inherited),
        'inherited_manifests_report_no_scientific_rewrite': all(
            row.get('scientific_content_rewritten') is False for row in inherited),
    }
    result['usage'] = {phase: read(ROOT / f'runs/optical/ours/{phase}/usage.json')
                       for phase in ['generation', 'evaluation']}
    result['usage_scope'] = 'Current-root requests across successive continuations; unknown requests remain reserved, not zero.'
    evaluation = ROOT / 'runs/optical/ours/evaluation/STATUS.json'
    result['evaluation'] = read(evaluation) if evaluation.exists() else {'status': 'pending'}
    (ROOT / 'AUDIT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
