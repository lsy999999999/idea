"""Regression cases from the five reproduced review findings; no live model/network calls."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from analysis_executor import AnalysisExecutor, expression
from fish_inquiry import InquiryPilot, RecordLedger
from fish_materials import CASE, Broker, digest
from inquiry_services import InquiryBroker, NoteGate
from knowledge_broker import KnowledgeBroker, SourcePolicy
from note_dependencies import prepare_dependencies
from prepare import HERE, PROJECT, save
from question_state import QuestionState
from final_evaluation import evaluate_final
sys.path.insert(0, str(PROJECT / 'src'))
sys.path.insert(0, str(PROJECT / 'bootstrap'))
from learning_memory import Memory
from novelty_fixtures import claim_report, scope_report
from novelty_scope import date_interval
from test_fish_inquiry import result as base

CONFIG = json.loads((HERE/'configs/fish_v2.json').read_text())


def shell(root):
    pilot = InquiryPilot.__new__(InquiryPilot)
    pilot.run = root/'run'; pilot.run.mkdir()
    pilot.case = CASE
    pilot.task_id, pilot.timeout, pilot.config = 'review/probe', 1, CONFIG
    pilot.broker = InquiryBroker(CASE, pilot.run/'services', CONFIG, fetch=lambda _: '{}')
    pilot.memory = Memory(root/'memory')
    pilot.questions = QuestionState(pilot.run/'questions', ['animal_behaviorist'])
    pilot.evidence = RecordLedger(pilot.run/'internal_verification')
    pilot.state, pilot.state_path = {'stages': {}}, pilot.run/'state.json'
    return pilot


class ArraySemantics(unittest.TestCase):
    def test_default_difference_and_norm_follow_time_and_vector_axes(self):
        positions = np.zeros((5, 2, 2))
        positions[:, 0, 0] = np.arange(5)*2
        positions[:, 1, 1] = np.arange(5)*3
        velocity = expression('diff(p)', {'p': positions})
        self.assertEqual(velocity.shape, (4, 2, 2))
        speeds = expression('norm(v)', {'v': velocity})
        np.testing.assert_array_equal(speeds, np.tile([2., 3.], (4, 1)))
        np.testing.assert_array_equal(expression('diff(p, axis=2)', {'p': positions}), np.diff(positions, axis=2))
        self.assertEqual(expression('norm(v, axis=None)', {'v': velocity}), np.linalg.norm(velocity))

    def test_executor_returns_per_fish_speed_array_with_documented_defaults(self):
        positions = np.zeros((6, 2, 2)); positions[:, :, 0] = np.arange(6)[:, None]*4
        plan = {'kind': 'analysis', 'record_id': 'R01', 'question': 'Per-fish speed?',
                'outputs': [{'name': 'speed', 'expression': 'norm(diff(positions))'}]}
        broker = Broker(CASE)
        with tempfile.TemporaryDirectory() as tmp, patch.object(broker, 'arrays', return_value=(positions, np.zeros((6,2)))):
            value = AnalysisExecutor(broker, tmp).execute(plan, 'speed')['result']
            np.testing.assert_array_equal(np.load(value['full_outputs'])['output_0'], np.full((5, 2), 4.))


class AbstractFallback(unittest.TestCase):
    def probe(self, date='2001-01-01', full_doi='10.12/old', full_text='Actual old body.'):
        calls = []
        def fetch(url):
            calls.append(url)
            if 'fullTextXML' in url:
                return '<article><front><article-id pub-id-type="doi">'+full_doi+'</article-id></front><body><p>'+full_text+'</p></body></article>'
            if 'europepmc' in url:
                return json.dumps({'resultList': {'result': [{'title': 'Old foundation', 'doi': '10.12/old',
                    'pmcid': 'PMC123', 'firstPublicationDate': date}]}})
            return '{}'
        with tempfile.TemporaryDirectory() as tmp:
            answer = KnowledgeBroker(tmp, SourcePolicy(CONFIG), fetch).search({'queries': ['foundation']}, 'test')
        return answer, calls

    def test_missing_abstract_still_fetches_eligible_fulltext(self):
        answer, calls = self.probe()
        self.assertTrue(any('fullTextXML' in url for url in calls))
        self.assertEqual(answer['sources'][0]['text'], 'Actual old body.')

    def test_ineligible_date_is_rejected_before_fetching_body(self):
        answer, calls = self.probe(date='2017-01-01')
        self.assertFalse(any('fullTextXML' in url for url in calls))
        self.assertEqual(answer['sources'], [])

    def test_mismatched_or_excluded_fulltext_stays_unavailable(self):
        for kwargs in ({'full_doi': '10.12/other'}, {'full_text': CONFIG['excluded_titles'][0]}):
            with self.subTest(kwargs=kwargs):
                answer, calls = self.probe(**kwargs)
                self.assertTrue(any('fullTextXML' in url for url in calls))
                self.assertEqual(answer['sources'], [])


class NoteClosure(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pilot = shell(self.root)

    def old_answer(self):
        p = self.pilot
        packet = NoteGate(p.broker, [p.memory.root, CASE/'researchers']).retrieve(
            'animal_behaviorist', 'fish coordinates', self.root/'packet/memory_retrieval/test.json')
        note = next(n['note'] for n in packet['retrieved'] if n['note']['kind'] == 'correction')
        p.packet = lambda sid, rid: packet
        answer = {**base(), 'initial_question': 'Which descriptions remain useful?',
            'memory_notes': [{**note, 'revision_reason': 'Retain the audited correction history.'}],
            'exploration': {'missing_external_facts': [], 'unselected_definitions': [], 'interface_gaps': [],
                'next_action': 'Compare descriptions', 'stalled_reason': '', 'understanding_changed': False}}
        return packet, note, answer

    def test_real_old_correction_survives_recommit_and_local_retrieval(self):
        packet, note, answer = self.old_answer()
        with patch('fish_inquiry.invoke', return_value=answer):
            self.pilot.call('01_initial_0', 'animal_behaviorist', 'Review', {})
        self.assertIn('01_initial_0', self.pilot.state['stages'])
        stored = json.loads(Path(self.pilot.memory.index('animal_behaviorist')['notes'][note['key']]['path']).read_text())
        self.assertEqual(stored['sources'], note['sources'])
        again = NoteGate(self.pilot.broker, [self.pilot.memory.root]).retrieve(
            'animal_behaviorist', 'fish', self.root/'later/memory_retrieval/test.json')
        self.assertEqual(again['retrieved'][0]['note']['key'], note['key'])
        self.assertEqual(set(again['retrieved'][0]['source_dependencies']), set(next(
            item['source_dependencies'] for item in packet['retrieved'] if item['note']['key'] == note['key'])))

    def test_unverified_inherited_dependency_fails_before_memory_commit(self):
        packet, note, answer = self.old_answer()
        for item in packet['retrieved']:
            item.pop('dependency_schema')
        with patch('fish_inquiry.invoke', return_value=answer), self.assertRaisesRegex(ValueError, 'Unverified memory dependency'):
            self.pilot.call('01_initial_0', 'animal_behaviorist', 'Review', {})
        self.assertEqual(self.pilot.memory.index('animal_behaviorist')['notes'], {})
        self.assertFalse((self.pilot.run/'stages/01_initial_0/admission.json').exists())

    def test_revising_inherited_note_cannot_drop_its_correction_reports(self):
        _, note, answer = self.old_answer()
        answer['memory_notes'][0]['sources'] = ['measurements.json']
        with patch('fish_inquiry.invoke', return_value=answer), self.assertRaisesRegex(ValueError, 'previous correction sources'):
            self.pilot.call('01_initial_0', 'animal_behaviorist', 'Review', {})
        self.assertEqual(self.pilot.memory.index('animal_behaviorist')['notes'], {})

    def test_interrupted_commit_resumes_without_new_model_call_or_note_version(self):
        _, note, answer = self.old_answer()
        with patch('fish_inquiry.invoke', return_value=answer), patch.object(self.pilot.questions, 'accept', side_effect=OSError('simulated interruption')):
            with self.assertRaises(OSError):
                self.pilot.call('01_initial_0', 'animal_behaviorist', 'Review', {})
        before = self.pilot.memory.index('animal_behaviorist')
        self.assertNotIn('01_initial_0', self.pilot.state['stages'])
        with patch('fish_inquiry.invoke', side_effect=AssertionError('Do not regenerate admitted content')):
            self.pilot.call('01_initial_0', 'animal_behaviorist', 'Review', {})
        self.assertEqual(before, self.pilot.memory.index('animal_behaviorist'))
        self.assertIn('01_initial_0', self.pilot.state['stages'])

    def test_report_closure_keeps_upstream_and_cited_sources_under_earlier_cutoff(self):
        p = self.pilot
        for key, year in [('upstream', '2007'), ('verifier', '2008')]:
            p.broker.sources[key] = {'id': key, 'doi': 'https://example.org/'+key, 'date': year+'-01-01', 'text': 'Synthetic source'}
        premise = {'id': 'p', 'text': 'Upstream premise', 'kind': 'inference', 'use': 'exploratory',
            'consequence': '', 'basis': {'source_ids': ['upstream'], 'record_ids': []}, 'depends_on': []}
        target = {'id': 'q', 'text': 'A decision', 'kind': 'inference', 'use': 'research_decision',
            'consequence': 'Choose a comparison', 'basis': {'source_ids': [], 'record_ids': ['R01']}, 'depends_on': ['s:p']}
        answer = {**base(), 'evidence_claims': [premise, target]}
        source_path = self.root/'original.json'; save(source_path, answer)
        p.evidence.observe('s', 'animal_behaviorist', answer, source_path)
        report = {'findings': [{'claim_ref': 's:q', 'status': 'supported', 'reason': 'Synthetic',
            'evidence_refs': ['source:verifier'], 'corrected_claim': None}]}
        report_path = self.root/'report.json'; save(report_path, report)
        p.evidence.record_report('boundary', report, report_path)
        note = {'key': 'dependency', 'title': 'Dependency', 'kind': 'correction', 'mastery': 'explained',
            'understanding': 'Depends on the premise', 'conditions': 'Synthetic', 'example': 'Comparison',
            'open_questions': 'More comparisons?', 'tags': ['fish'], 'sources': [str(report_path.resolve())]}
        result = {**base(), 'memory_notes': [note]}
        context = {'_stage': 'uptake', 'affected_claims': p.evidence.relevant(['s:q']),
                   'verification_report_path': str(report_path.resolve())}
        prepared = prepare_dependencies(p, result, context)
        self.assertEqual(set(prepared['dependency']['source_dependencies']),
            {'measurements.json', 'https://example.org/upstream', 'https://example.org/verifier'})
        path = self.root/'note_result.json'; save(path, result)
        p.memory.commit('animal_behaviorist', p.task_id, 'uptake', path)
        p.record_note_dependencies('animal_behaviorist', result, context, prepared)
        p.broker.policy = SourcePolicy({**CONFIG, 'knowledge_before_exclusive': '2000-01-01'})
        packet = NoteGate(p.broker, [p.memory.root]).retrieve('animal_behaviorist', 'fish', self.root/'new/memory_retrieval/probe.json')
        self.assertEqual(packet['retrieved'], [])

    def test_old_incomplete_local_reviews_are_not_trusted(self):
        _, note, answer = self.old_answer()
        with patch('fish_inquiry.invoke', return_value=answer):
            self.pilot.call('01_initial_0', 'animal_behaviorist', 'Review', {})
        reviews_path = self.pilot.broker.root/'note_reviews.json'
        reviews = json.loads(reviews_path.read_text())
        for review in reviews.values():
            review.pop('dependency_schema')
        save(reviews_path, reviews)
        packet = NoteGate(self.pilot.broker, [self.pilot.memory.root]).retrieve(
            'animal_behaviorist', 'fish', self.root/'new/memory_retrieval/probe.json')
        self.assertEqual(packet['retrieved'], [])


class FinalCheck(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=HERE)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pilot = shell(self.root)
        self.ideas = [{'id': 'I1', 'title': 'An idea', 'idea': 'An independently proposed question.'}]
        prompt = self.pilot.run/'stages/initial/attempt-001/prompt.txt'
        prompt.parent.mkdir(parents=True); prompt.write_text('Screened measurements and historical material only.')
        audit = prompt.with_name('execution_audit.json'); save(audit, {'tool_events': 0, 'returncode': 0})
        idea_path = self.pilot.run/'ideas.json'; save(idea_path, {'ideas': self.ideas})
        save(self.pilot.run/'GENERATION_FREEZE.json', {'files': {str(p.resolve()): digest(p) for p in (prompt, audit, idea_path)}})

    def stage(self, run, stage, role, prompt, inputs, model, effort, timeout):
        self.assertEqual((role, model, effort), ('idea_check_agent', 'gpt-6-luna', 'low'))
        self.assertIn('Independently search', prompt)
        ideas = json.loads(inputs[0].read_text())['ideas']
        report = claim_report(ideas, run/'fixture', known_direction=True)
        for idea, check in zip(ideas, report['checks']):
            origin = idea['evaluation_context']['source_papers'][0]
            check['prior_work']['sources'][0].update(url=origin['urls'][0], title=origin['title'])
            comparison = check['novelty']['comparisons'][0]
            for facet in comparison['facets']:
                comparison['facets'][facet] = copy.deepcopy(comparison['facets']['contribution'])
            scope_report(idea, check, run/'fixture')
        path = run/'result.json'; save(path, report)
        return path, report

    def test_shared_checker_accepts_hidden_origin_rediscovery_after_freeze_and_caches(self):
        before = digest(self.pilot.run/'GENERATION_FREEZE.json')
        with patch('final_evaluation.stage_run', side_effect=self.stage) as call:
            report = evaluate_final(self.pilot, self.ideas)
            again = evaluate_final(self.pilot, self.ideas)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(report, again)
        self.assertEqual(report['schema_version'], 'claim-centric-v2')
        assessment = report['checks'][0]['novelty']['assessment']
        self.assertEqual(assessment['task_verdict'], 'INDEPENDENT_REDISCOVERY')
        self.assertTrue(assessment['candidate_retained'])
        self.assertEqual(assessment['context']['reference_date']['evidence_kind'], 'task_configuration')
        self.assertEqual(assessment['context']['reference_date']['earliest'], '2010-01-01')
        self.assertEqual(digest(self.pilot.run/'GENERATION_FREEZE.json'), before)
        self.assertEqual(self.pilot.memory.index('animal_behaviorist')['notes'], {})
        original = json.loads((self.pilot.run/'ideas.json').read_text())
        self.assertNotIn('evaluation_context', original['ideas'][0])

    def test_old_empty_coverage_witness_is_rejected(self):
        answer = {**base(), 'checks': [{'idea_id': 'I1',
            'prior_work': {'verdict': 'close_direction_found', 'reason': 'Unsupported', 'sources': []},
            'math': {'verdict': 'no_obvious_error', 'reason': 'Coherent', 'errors': []},
            'novelty': {'coverage': 'covered', 'core_claims': []}}]}
        with self.assertRaises(ValueError):
            self.pilot.validate('06_final_check', 'historical_final_evaluator', answer, {'ideas': self.ideas}, False, False)

    def test_task_reference_cannot_be_reused_as_publication_date(self):
        with patch('final_evaluation.stage_run', side_effect=self.stage):
            report = evaluate_final(self.pilot, self.ideas)
        reference = report['checks'][0]['novelty']['assessment']['context']['reference_date']
        with self.assertRaisesRegex(ValueError, 'cannot establish a source publication'):
            date_interval(reference, PROJECT)

    def test_changed_generation_blocks_evaluation_before_model_call(self):
        (self.pilot.run/'ideas.json').write_text('{}')
        with patch('final_evaluation.stage_run', side_effect=AssertionError('No call expected')), self.assertRaisesRegex(ValueError, 'Generation changed'):
            evaluate_final(self.pilot, self.ideas)

    def test_unaudited_generation_does_not_claim_hidden_exposure(self):
        audit = self.pilot.run/'stages/initial/attempt-001/execution_audit.json'
        save(audit, {'tool_events': 1})
        freeze_path = self.pilot.run/'GENERATION_FREEZE.json'
        freeze = json.loads(freeze_path.read_text()); freeze['files'][str(audit.resolve())] = digest(audit); save(freeze_path, freeze)
        with patch('final_evaluation.stage_run', side_effect=self.stage):
            report = evaluate_final(self.pilot, self.ideas)
        self.assertEqual(report['checks'][0]['novelty']['assessment']['task_verdict'], 'UNRESOLVED')


if __name__ == '__main__':
    unittest.main()
