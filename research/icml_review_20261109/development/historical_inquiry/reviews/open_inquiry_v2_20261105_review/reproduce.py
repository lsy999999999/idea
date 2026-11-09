"""Read-only review probes; all writes go to temporary directories, no model/network calls."""
import copy
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

PROJECT = Path('/Applications/ideas/1103_boundary_discovery')
sys.path.insert(0, str(PROJECT / 'historical_inquiry'))
sys.path.insert(0, str(PROJECT / 'src'))
import numpy as np
from analysis_executor import expression
from fish_inquiry import InquiryPilot, RecordLedger
from fish_materials import CASE, digest
from inquiry_services import InquiryBroker, NoteGate
from knowledge_broker import KnowledgeBroker, SourcePolicy
from learning_memory import Memory
from question_state import QuestionState
from prepare import save

CONFIG = json.loads((PROJECT / 'historical_inquiry/configs/fish_v2.json').read_text())
RESULTS = {}


def base():
    return {'summary': 'Synthetic review probe', 'artifacts': [], 'evidence': [], 'claims': [],
            'limitations': [], 'next_actions': [], 'evidence_claims': [], 'doubts': []}


def pilot_shell(root):
    p = InquiryPilot.__new__(InquiryPilot)
    p.run = root / 'run'
    p.run.mkdir()
    p.task_id = 'review/probe'
    p.timeout = 1
    p.config = CONFIG
    p.broker = InquiryBroker(CASE, p.run / 'services', CONFIG, fetch=lambda _: '{}')
    p.memory = Memory(root / 'memory')
    p.questions = QuestionState(p.run / 'questions', ['animal_behaviorist'])
    p.evidence = RecordLedger(p.run / 'evidence')
    p.state = {'stages': {}}
    p.state_path = p.run / 'state.json'
    return p


# 1. These calls follow the default axes explicitly documented in PLAN_PROTOCOL.
x = np.array([[0., 10.], [2., 10.], [4., 10.]])
RESULTS['documented_defaults'] = {
    'diff_actual': expression('diff(x)', {'x': x}).tolist(),
    'diff_expected_axis_0': np.diff(x, axis=0).tolist(),
    'norm_actual': expression('norm(x)', {'x': x}).tolist(),
    'norm_expected_axis_minus_1': np.linalg.norm(x, axis=-1).tolist(),
}
assert RESULTS['documented_defaults']['diff_actual'] != RESULTS['documented_defaults']['diff_expected_axis_0']
assert np.ndim(RESULTS['documented_defaults']['norm_actual']) == 0

# 2. Reusing a real, audited old correction passes admission, then fails AFTER commit.
with tempfile.TemporaryDirectory() as tmp:
    p = pilot_shell(Path(tmp))
    packet = NoteGate(p.broker, [p.memory.root, CASE/'researchers']).retrieve(
        'animal_behaviorist', 'fish coordinates', Path(tmp)/'packet/memory_retrieval/test.json')
    old = next(item['note'] for item in packet['retrieved'] if item['note']['kind'] == 'correction')
    p.packet = lambda sid, rid: packet
    result = base()
    result.update(initial_question='Which coordinate descriptions remain useful?', memory_notes=[{
        **old, 'revision_reason': 'Retain the audited source and correction history.'}],
        exploration={'missing_external_facts': [], 'unselected_definitions': [], 'interface_gaps': [],
                     'next_action': 'Compare descriptions', 'stalled_reason': '', 'understanding_changed': False})
    error = None
    with patch('fish_inquiry.invoke', return_value=result):
        try:
            p.call('01_initial_0', 'animal_behaviorist', 'Synthetic initial review', {}, notes=True)
        except ValueError as exc:
            error = str(exc)
    RESULTS['old_correction_reuse'] = {'error': error,
        'memory_already_committed': old['key'] in p.memory.index('animal_behaviorist')['notes'],
        'stage_marked_complete': '01_initial_0' in p.state['stages']}
    assert error == 'Unverified memory dependency'
    assert RESULTS['old_correction_reuse']['memory_already_committed']
    assert not RESULTS['old_correction_reuse']['stage_marked_complete']

    # 3. A positive final novelty conclusion needs no witness under this entry.
    final = base()
    final['checks'] = [{'idea_id': 'Q1',
        'prior_work': {'verdict': 'close_direction_found', 'reason': 'Synthetic assertion', 'sources': []},
        'math': {'verdict': 'no_obvious_error', 'reason': 'Synthetic assertion', 'errors': []},
        'novelty': {'coverage': 'covered', 'core_claims': [], 'reason': 'No source evidence'}}]
    p.validate('06_final_check', 'historical_final_evaluator', final, {'ideas': [{'id': 'Q1'}]}, False, False)
    RESULTS['unsupported_final_coverage'] = {'accepted': True, 'sources': 0, 'core_claims': 0}

# 4. No abstract -> the broker never attempts the available, date-eligible PMC body.
with tempfile.TemporaryDirectory() as tmp:
    calls = []
    def fetch(url):
        calls.append(url)
        if 'fullTextXML' in url:
            return '<article><front><article-id pub-id-type="doi">10.12/old</article-id></front><body><p>Readable old foundation.</p></body></article>'
        if 'europepmc' in url:
            return json.dumps({'resultList': {'result': [{'title': 'Old full-text foundation',
                'doi': '10.12/old', 'pmcid': 'PMC123', 'firstPublicationDate': '2001-01-01'}]}})
        return '{}'
    answer = KnowledgeBroker(tmp, SourcePolicy(CONFIG), fetch).search({'queries': ['foundation']}, 'probe')
    RESULTS['abstract_missing_fulltext_available'] = {'sources_returned': len(answer['sources']),
        'fulltext_requested': any('fullTextXML' in url for url in calls), 'attempts': answer['attempts']}
    assert not answer['sources'] and not RESULTS['abstract_missing_fulltext_available']['fulltext_requested']

# 5. A verification-derived note loses the source of its premise in the dependency record.
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    p = pilot_shell(root)
    source = {'id': 'late', 'doi': 'https://example.org/2007', 'date': '2007-01-01', 'text': 'Synthetic premise.'}
    p.broker.sources['late'] = source
    premise = {'id': 'p', 'text': 'A premise from 2007', 'kind': 'inference', 'use': 'exploratory',
               'consequence': 'Basis for subsequent decision', 'basis': {'source_ids': ['late'], 'record_ids': []}, 'depends_on': []}
    target = {'id': 'q', 'text': 'A decision depending on that premise', 'kind': 'inference', 'use': 'research_decision',
              'consequence': 'Choose a comparison', 'basis': {'source_ids': [], 'record_ids': ['R01']}, 'depends_on': ['s:p']}
    original = {**base(), 'evidence_claims': [premise, target]}
    original_path = root/'original.json'; save(original_path, original)
    p.evidence.observe('s', 'animal_behaviorist', original, original_path)
    report_path = root/'report.json'
    report = {'findings': [{'claim_ref': 's:q', 'status': 'supported', 'reason': 'Synthetic premise chain',
                            'evidence_refs': ['source:late'], 'corrected_claim': None}]}
    save(report_path, report)
    p.evidence.record_report('boundary', report, report_path)
    note = {'key': 'dependent_knowledge', 'title': 'Dependent knowledge', 'kind': 'correction', 'mastery': 'explained',
            'understanding': 'A consequence of the upstream source', 'conditions': 'Synthetic test', 'example': 'A scoped comparison',
            'open_questions': 'Further comparison', 'tags': ['fish'], 'sources': [str(report_path.resolve())]}
    result = {**base(), 'memory_notes': [note]}
    result_path = root/'note_result.json'; save(result_path, result)
    p.memory.commit('animal_behaviorist', 'review/task', 'after_report', result_path)
    affected = p.evidence.relevant(['s:q'])
    p.record_note_dependencies('animal_behaviorist', result, {
        'verification_report_path': str(report_path.resolve()), 'affected_claims': affected})
    reviews = json.loads((p.broker.root/'note_reviews.json').read_text())
    recorded = next(iter(reviews.values()))['source_dependencies']
    p.broker.policy = SourcePolicy({**CONFIG, 'knowledge_before_exclusive': '2000-01-01'})
    replay = NoteGate(p.broker, [p.memory.root]).retrieve('animal_behaviorist', 'fish', root/'new/memory_retrieval/replay.json')
    RESULTS['transitive_dependency_missing'] = {'actual_ancestor_source_date': source['date'],
        'recorded_dependencies': recorded, 'new_cutoff': '2000-01-01', 'note_returned': bool(replay['retrieved'])}
    assert source['doi'] not in recorded and replay['retrieved']

out = Path(__file__).with_name('results.json')
out.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(RESULTS, ensure_ascii=False, indent=2))
