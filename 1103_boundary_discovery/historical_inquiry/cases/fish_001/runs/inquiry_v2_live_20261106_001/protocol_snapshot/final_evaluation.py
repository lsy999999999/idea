"""After-freeze adapter to the shared six-facet, temporal/exposure-aware checker."""
import copy
import hashlib
import json
from pathlib import Path
import sys

from prepare import PROJECT, save
sys.path.insert(0, str(PROJECT / 'src'))
from discover import stage_run
from idea_check import CHECKER_PROMPT, POLICY, SCHEMA_VERSION, validate_checks, validate_ideas
from knowledge_broker import doi_key


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_write(path, value):
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError('Frozen evaluation input changed: ' + str(path))
    else:
        save(path, value)


def evaluation_context(pilot):
    """Record the configured historical boundary and audit actual generation inputs."""
    freeze_path = pilot.run / 'GENERATION_FREEZE.json'
    freeze = json.loads(freeze_path.read_text())
    for path, expected in freeze['files'].items():
        if file_hash(path) != expected:
            raise ValueError('Generation changed before final evaluation')
    root = pilot.run / 'evaluation'
    config_path = root / 'task_reference.json'
    cutoff = pilot.config['knowledge_before_exclusive']
    frozen_write(config_path, {'knowledge_before_exclusive': cutoff,
        'reference_kind': 'Configured task boundary, not a source-publication reconstruction.'})
    restriction = json.loads((pilot.case / 'controller_only/restriction.json').read_text())
    origin = restriction['source_paper']
    tokens = [doi_key(origin['id']).casefold(), origin['title'].casefold()]
    prompts = [Path(path) for path in freeze['files'] if Path(path).name == 'prompt.txt']
    hits, unaudited = [], []
    for path in prompts:
        if any(token in path.read_text().casefold() for token in tokens):
            hits.append(str(path))
        audit_path = path.parent / 'execution_audit.json'
        if str(audit_path.resolve()) not in freeze['files']:
            unaudited.append(str(path))
        else:
            audit = json.loads(audit_path.read_text())
            if audit.get('tool_events') != 0:
                unaudited.append(str(path))
    policy_passed = (doi_key(origin['id']) in pilot.broker.policy.dois
                     and all(not pilot.broker.policy.rejection(s) for s in pilot.broker.sources.values()))
    hidden = bool(prompts) and not hits and not unaudited and policy_passed
    status = 'hidden' if hidden else 'unknown'
    quote = 'Origin idea exposure in screened generation inputs: ' + status
    audit_path = root / 'generation_exposure.json'
    frozen_write(audit_path, {'assessment': quote, 'origin': origin,
        'generation_freeze_sha256': file_hash(freeze_path), 'prompt_count': len(prompts),
        'identity_hits': hits, 'unaudited_prompts': unaudited, 'generation_source_policy_passed': policy_passed,
        'scope': 'Supplied inputs/tools/memory only; not a pretraining-knowledge audit.'})
    return {'mode': 'historical',
        'reference_date': {'earliest': cutoff, 'latest': cutoff, 'evidence_kind': 'task_configuration',
                           'snapshot_path': str(config_path.resolve()),
                           'quote': '"knowledge_before_exclusive": "' + cutoff + '"'},
        'reference_reason': 'Use the approved task knowledge cutoff, exclusive. This is not the originating paper publication date.',
        'source_papers': [{'paper_id': 'origin_1', 'title': origin['title'], 'urls': [origin['id']],
            'idea_exposure': {'status': status, 'reason': 'Frozen prompt/tool/source audit; screened raw measurements are permitted.',
                              'snapshot_path': str(audit_path.resolve()), 'quote': quote}}]}


def evaluate_final(pilot, ideas):
    """Fresh literature retrieval is allowed only in this isolated post-generation stage."""
    root = pilot.run / 'evaluation'
    context = evaluation_context(pilot)
    evaluated = [{**copy.deepcopy(idea), 'evaluation_context': copy.deepcopy(context)} for idea in ideas]
    if evaluated:
        validate_ideas({'ideas': evaluated})
    idea_path = root / 'ideas.json'
    frozen_write(idea_path, {'ideas': evaluated, 'source': str((pilot.run / 'ideas.json').resolve())})
    evidence_path = root / 'generation_evidence.json'
    frozen_write(evidence_path, {'generation_freeze': str((pilot.run / 'GENERATION_FREEZE.json').resolve()),
        'seed_sources': [pilot.broker.sources[key] for key in sorted(pilot.broker.sources)],
        'measurement_metadata': pilot.broker.catalog,
        'purpose': 'Starting evidence only. Perform independent prior-work retrieval and verify source identities/dates.'})
    receipt_path = root / 'ACCEPTED_CHECK.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt['ideas_sha256'] != file_hash(idea_path) or file_hash(receipt['result_path']) != receipt['result_sha256']:
            raise ValueError('Accepted final check input/output changed')
        result = json.loads(Path(receipt['result_path']).read_text())
    elif evaluated:
        prompt = CHECKER_PROMPT + '''
This is evaluation AFTER the generation freeze. The origin and later literature may now
be retrieved to assess rediscovery and contemporary overlap. The experiment's historical
reference is the explicitly configured task cutoff, not an inferred publication date.
Use the supplied context unchanged. Independently search problem/mechanism/contribution;
the generation seed corpus is not the search universe. Verify first public dates and
bind each title/DOI to actual retrieved content. Output the full claim-centric-v2 report.
Keep all evaluation files in this stage's workspace; never write researcher memories,
generation artifacts or source code. Return no memory_notes. This check is terminal.
'''
        result_path, result = stage_run(root, 'check', 'idea_check_agent', prompt,
            [idea_path, POLICY, evidence_path], 'gpt-6-luna', 'low', pilot.config.get('check_timeout', 900))
        validate_checks(result, evaluated, require_claims=True)
        if result.get('memory_notes'):
            raise ValueError('Final evaluation must not produce memory updates')
        frozen_write(receipt_path, {'schema_version': SCHEMA_VERSION, 'requested_model': 'gpt-6-luna',
            'ideas_sha256': file_hash(idea_path), 'result_path': str(result_path.resolve()),
            'result_sha256': file_hash(result_path)})
    else:
        result = {'schema_version': SCHEMA_VERSION, 'checks': [], 'searches': [],
                  'reason': 'No frozen candidate; no evaluator call required.'}
    validate_checks(result, evaluated, require_claims=True)
    if result.get('memory_notes'):
        raise ValueError('Final evaluation must not produce memory updates')
    return result
