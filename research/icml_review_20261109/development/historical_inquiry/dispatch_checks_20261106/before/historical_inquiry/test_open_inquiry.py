"""Contract and integration tests for online supply, computation and historical isolation."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import sys
from unittest.mock import patch

import numpy as np

from analysis_executor import AnalysisExecutor, expression, rolling, shift
from fish_materials import Broker, CASE, digest
from fish_inquiry import InquiryPilot, RESEARCHERS, RecordLedger
from inquiry_services import InquiryBroker, NoteGate
from knowledge_broker import KnowledgeBroker, SourcePolicy
from prepare import HERE, save
from test_fish_inquiry import result, claim
from test_question_state import decision
from test_hypothesis_development import card
sys.path.insert(0, str(HERE.parent / 'bootstrap'))
from novelty_fixtures import claim_report

CONFIG = json.loads((HERE / 'configs/fish_v2.json').read_text())


def frozen_memory_case():
    """Use the original immutable fixture; copied indexes retain absolute provenance."""
    index = json.loads((CASE/'researchers/animal_behaviorist/index.json').read_text())
    item = next(iter(index['notes'].values()))
    note = json.loads(Path(item['path']).read_text())
    case_name, run_id = note['source_task'].split('/', 1)
    source = Path(note['source_result'])
    original = next(p for p in source.parents if p.name == case_name and
                    (p/'runs'/run_id) in source.parents)
    if (original/'controller_only/allowed_hashes.json').read_bytes() != (CASE/'controller_only/allowed_hashes.json').read_bytes():
        raise ValueError('Original frozen fixture differs from this case')
    return original


class KnowledgeTests(unittest.TestCase):
    def test_date_exclusion_and_failed_provider_fallthrough(self):
        calls = []
        def fetch(url):
            calls.append(url)
            if 'europepmc' in url:
                return json.dumps({'resultList': {'result': [
                    {'title': 'unknown', 'abstractText': 'date unknown'},
                    {'title': 'later', 'firstPublicationDate': '2010-01-01', 'abstractText': 'LATER_TEXT'},
                    {'doi': CONFIG['excluded_dois'][0], 'firstPublicationDate': '2000-01-01', 'abstractText': 'HIDDEN_TEXT'}]}})
            if 'crossref' in url:
                raise RuntimeError('provider down')
            return json.dumps({'results': [{'title': 'A foundational model', 'publication_date': '2003-12-01',
                'doi': 'https://doi.org/10.1234/foundation', 'abstract_inverted_index': {'A': [0], 'real': [1], 'model': [2]}}]})
        with tempfile.TemporaryDirectory() as tmp:
            broker = KnowledgeBroker(tmp, SourcePolicy(CONFIG), fetch)
            r = broker.search({'queries': ['foundation model example'], 'material_types': ['book', 'tutorial']}, 'q')
            self.assertEqual(len(r['sources']), 1)
            self.assertEqual(r['sources'][0]['text'], 'A real model')
            self.assertEqual(len(calls), 3)
            self.assertNotIn('HIDDEN_TEXT', json.dumps(r))
            self.assertNotIn('LATER_TEXT', json.dumps(r))
            self.assertEqual(r, broker.search(r['request'], 'q'))
            self.assertEqual(len(calls), 3)
            accepted_path = next((Path(tmp)/'accepted').glob('*.json'))
            tampered = json.loads(accepted_path.read_text()); tampered['text'] = 'Changed scientific content'
            save(accepted_path, tampered)
            with self.assertRaisesRegex(ValueError, 'content hash'):
                KnowledgeBroker(tmp, SourcePolicy(CONFIG), fetch)
            self.assertEqual(len(list((Path(tmp)/'controller_only/q').glob('*.json'))), 3)

    def test_task_cutoff_is_not_global_and_origin_content_is_excluded(self):
        config = {**CONFIG, 'knowledge_before_exclusive': '1990-01-01'}
        policy = SourcePolicy(config)
        self.assertEqual(policy.rejection({'date': '2000-01-01', 'text': 'ok'}), 'outside_task_date_boundary')
        self.assertEqual(policy.rejection({'date': '1980-01-01', 'text': CONFIG['excluded_titles'][0]}), 'excluded_origin_or_content')
        row = KnowledgeBroker.normalize('crossref', {'published': {'date-parts': [[1989]]}, 'title': ['Old'], 'abstract': 'text'})
        self.assertEqual(row['date'], '1989-12-31')
        self.assertIsNone(policy.rejection(row))

    def test_fulltext_requires_matching_doi_and_read_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = KnowledgeBroker(tmp, SourcePolicy(CONFIG))
            xml = '<article><front><article-id pub-id-type="doi">10.12/a</article-id></front><body><sec><p>Actual model explanation.</p></sec></body><back><p>Not supplied</p></back></article>'
            self.assertEqual(b.article_text(xml, {'doi': 'https://doi.org/10.12/a'}), 'Actual model explanation.')
            with self.assertRaises(ValueError):
                b.article_text(xml, {'doi': '10.12/b'})


class AnalysisTests(unittest.TestCase):
    def test_expressions_cannot_execute_code_or_access_files(self):
        for text in ['__import__(1)', 'positions.__class__', 'open(1)', '[x for x in positions]']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                expression(text, {'positions': np.arange(3)})
        np.testing.assert_allclose(shift(np.arange(5.), 2)[2:], [0,1,2])
        np.testing.assert_allclose(rolling(np.array([1.,2.,np.nan,4.,5.]), 2), [np.nan,1.5,np.nan,np.nan,4.5], equal_nan=True)

    def test_researcher_variables_conditional_comparison_and_model_are_executed(self):
        broker = Broker(CASE)
        t = np.arange(30.)
        p = np.zeros((30,2,2)); p[:,0,0] = t; p[:,1,0] = 2*t+3
        plan = {'kind': 'analysis', 'question': 'Compare an explicitly defined coordinate state', 'record_id': 'R01',
            'variables': [{'name': 'a', 'expression': 'positions[:,0,0]', 'meaning': 'A x', 'units': 'native'},
                          {'name': 'b', 'expression': 'positions[:,1,0]', 'meaning': 'B x', 'units': 'native'}],
            'outputs': [{'name': 'difference', 'expression': 'b-a'}],
            'groups': [{'name': 'chosen early state', 'where': 'a<10', 'values': ['b']}],
            'model': {'target': 'b', 'features': ['a'], 'train_fraction': .6}}
        with tempfile.TemporaryDirectory() as tmp, patch.object(broker, 'arrays', return_value=(p,np.zeros((30,2)))):
            executor = AnalysisExecutor(broker,tmp)
            r = executor.execute(plan,'one')['result']
            self.assertEqual(r['groups'][0]['selected_rows'], 10)
            np.testing.assert_allclose(r['model']['coefficients'], [3,2], atol=1e-10)
            self.assertLess(r['model']['evaluation_rmse'], 1e-10)
            self.assertEqual(np.load(r['full_outputs'])['output_0'].shape, (30,))
            self.assertEqual(executor.execute(plan,'one')['result'], r)

    def test_interface_gap_goes_to_controller_then_executes_or_remains_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            req = {'kind': 'custom', 'question': 'Compute a coordinate average', 'record_id': 'R01'}
            translated = {**req, 'outputs': [{'name': 'mean', 'expression': 'mean(positions)'}]}
            ex = AnalysisExecutor(Broker(CASE),tmp,lambda *a: translated)
            self.assertEqual(ex.execute(req,'resolved')['result']['status'], 'executed')
            self.assertEqual(json.loads((Path(tmp)/'resolved/controller_task.json').read_text())['status'], 'executed')
            ex.planner = None
            self.assertEqual(ex.execute(req,'pending')['result']['status'], 'pending_controller')


class MemoryAndReasoningTests(unittest.TestCase):
    def test_memory_screening_reuses_frozen_fish_notes_without_modifying_versions(self):
        import sys
        sys.path.insert(0, str(HERE.parent / 'src'))
        from learning_memory import Memory
        with tempfile.TemporaryDirectory() as tmp:
            case = frozen_memory_case()
            broker = InquiryBroker(case, Path(tmp)/'services', CONFIG, fetch=lambda _: '{}')
            local = Path(tmp)/'memory'; local.mkdir()
            gate = NoteGate(broker,[local,case/'researchers',HERE.parent/'learning_lab/researchers'])
            before = {str(p):digest(p) for p in (case/'researchers').rglob('*.json')}
            packet = gate.retrieve('nonequilibrium_physicist','motion history memory fish',Path(tmp)/'run/memory_retrieval/test.json')
            self.assertTrue(packet['retrieved'])
            self.assertTrue(all(n['note']['source_task'].startswith('fish_001/') for n in packet['retrieved']))
            self.assertEqual(before,{str(p):digest(p) for p in (case/'researchers').rglob('*.json')})

    def test_check_prioritizes_the_decision_to_stop_over_generic_scope_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = RecordLedger(Path(tmp)/'ledger',max_checks=1,batch_size=1)
            r = result()
            a, b = claim('limit'), claim('stop')
            a['consequence'] = 'Qualify an interpretation'
            b['consequence'] = '因此停止进一步数据分析'
            r['evidence_claims'] = [a,b]
            path = Path(tmp)/'result.json'; save(path,r)
            ledger.observe('discussion','researcher',r,path)
            batch = ledger.select('after')
            self.assertEqual(batch['targets'][0]['ref'],'discussion:stop')


class PipelineTests(unittest.TestCase):
    def test_online_requests_initial_and_return_learning_freeze_and_restart(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            case = Path(tmp)/'case'
            shutil.copytree(CASE/'allowed',case/'allowed')
            shutil.copytree(CASE/'controller_only',case/'controller_only')
            seen, searches, invocations = {}, [], []
            config = {**CONFIG, 'max_rounds': 2, 'max_internal_batches': 1, 'read_full_text': False}
            def fetch(url):
                searches.append(url)
                if 'europepmc' in url:
                    return json.dumps({'resultList': {'result': [{'title':'Foundation', 'doi':'10.12/old',
                        'firstPublicationDate':'2001-01-01', 'abstractText':'A real concept and its conditions.'}]}})
                return '{}'
            def fake(prompt, attempt, timeout):
                attempt = Path(attempt); attempt.mkdir(parents=True)
                (attempt/'prompt.txt').write_text(prompt)
                save(attempt/'execution_audit.json', {'returncode':0,'tool_events':0,'requested_model':'gpt-6-luna'})
                c = json.loads(prompt.split('INPUTS:\n',1)[1]); sid = c['_stage']; seen[sid] = c
                invocations.append(sid)
                r = result(); rid = c.get('researcher')
                if sid in {f'01_initial_{i}' for i in range(3)}:
                    self.assertEqual(c['evidence_state']['claims'], [])
                    r['initial_question'] = 'Personal question '+rid
                elif rid:
                    r['personal_question_update'] = decision(c['question_state']['self'])
                    r['shared_question_update'] = None
                    if sid.startswith('01_initial_'):
                        self.assertEqual(c['question_state']['peer_questions'], [])
                if rid:
                    self.assertIn('HYPOTHESIS DEVELOPMENT v1', prompt)
                    self.assertIn('NOT requirements', prompt)
                    if sid.startswith('01_initial_'):
                        self.assertEqual(c['hypothesis_state']['peer_branches'], [])
                    if sid in {f'01_initial_{i}' for i in range(3)}:
                        r['hypothesis_updates'] = [card()]
                    elif sid == '01_initial_0_learn_0':
                        self.assertEqual(c['hypothesis_state']['self'][0]['ref']['version'], 1)
                        r['hypothesis_updates'] = [card(base=1, implications=['If true, distinguish two cases'])]
                    elif sid == 'r1_return_1_learn_0':
                        r['hypothesis_updates'] = [card(base=1, conceptual_move='Separate two meanings')]
                    elif sid == '04_fresh_continuation':
                        self.assertEqual(c['hypothesis_state']['self'][0]['assumption'], card()['assumption'])
                        self.assertEqual(len(c['hypothesis_state']['peer_branches']), 2)
                    r['memory_notes'] = [{'key':'coordinate_state','title':'Coordinate state','kind':'interpretation',
                        'mastery':'explained','understanding':'A chosen observation definition', 'conditions':'Coordinates only',
                        'example':'Two tracked coordinates', 'open_questions':'Which useful state?', 'tags':['fish','state'],
                        'sources':['measurements.json'],'revision_reason':'Actual understanding retained'}]
                    for old in c.get('memory', {}).get('retrieved', []):
                        if old['note']['key'] == 'coordinate_state' and old['note']['kind'] == 'correction':
                            r['memory_notes'][0]['kind'] = 'correction'
                            r['memory_notes'][0]['sources'] = old['note']['sources']
                    r['learning_request'] = {'needed': sid in {'01_initial_0','r1_return_1'},
                        'queries':['a concept with a worked example'], 'gap':'Need useful foundation'}
                    r['exploration'] = {'missing_external_facts':[], 'unselected_definitions':['state'],
                        'interface_gaps':[], 'next_action':'Compare definitions', 'stalled_reason':'', 'understanding_changed':True}
                if sid == '01_initial_0':
                    r['evidence_claims'] = [claim('scope')]
                if sid.endswith('_verify'):
                    r['findings'] = [{'claim_ref':t['ref'],'status':'needs_correction','reason':'The claimed inference exceeds the evidence',
                        'evidence_refs':['motion:R01'],'corrected_claim':'Only a coordinate description is supported'} for t in c['targets']]
                if 'verification_report' in c:
                    r['verification_responses'] = [{'claim_ref':f['claim_ref'],'stance':'accept',
                        'reason':'Support is scoped','changed_understanding':'No change to the supported premise',
                        'question_effect':'retain'} for f in c['verification_report']['findings']]
                    r['memory_notes'] = [{**n, 'kind':'correction', 'revision_reason':'Actual correction',
                        'sources':list(set(n['sources']) | {c['verification_report_path']})} for n in c['affected_notes']]
                    if not r['memory_notes']:
                        r['memory_notes'] = []
                if sid == '05_candidates':
                    r['ideas'] = [{'id':'Q1','title':'Unfinished question','idea':'Unfinished question'}]
                    r['preserved_branches'] = [{'ref': c['ref'], 'reason': 'Retain unfinished assumption'}
                                              for c in c['current_hypotheses']]
                return r
            def fake_final(run, stage, role, prompt, inputs, model, effort, timeout):
                self.assertTrue((case/'runs/test/GENERATION_FREEZE.json').exists())
                self.assertEqual(role, 'idea_check_agent')
                self.assertIn('claim-centric-v2', prompt)
                ideas = json.loads(inputs[0].read_text())['ideas']
                checked = claim_report(ideas, run/'synthetic_evidence')
                path = run/'fixture_result.json'; save(path, checked)
                return path, checked
            with patch('fish_inquiry.invoke',side_effect=fake), patch('final_evaluation.stage_run',side_effect=fake_final):
                pilot = InquiryPilot(case,30,'test',config,fetch)
                with patch.object(pilot.evidence, 'observe', side_effect=OSError('interrupt after hypothesis commit')):
                    with self.assertRaises(OSError):
                        pilot.execute()
                self.assertEqual(len(pilot.hypotheses.current()), 1)
                initial_memory = copy.deepcopy(pilot.memory.index(RESEARCHERS[0][0]))
                pilot.execute()
                self.assertEqual(invocations.count('01_initial_0'), 1)
                initial_key = initial_memory['notes']['coordinate_state']
                self.assertTrue(Path(initial_key['path']).exists())
                self.assertEqual(digest(initial_key['path']), initial_key['sha256'])
            self.assertIn('r1_evidence_verify',seen)
            self.assertIn('01_initial_0_learn_0',seen)
            self.assertIn('r1_return_1_learn_0',seen)
            self.assertEqual(len(searches), 6)
            self.assertEqual(seen['01_initial_0_learn_0']['broker_reply']['sources'][0]['text'], 'A real concept and its conditions.')
            self.assertEqual(seen['01_initial_0']['measurement_metadata']['measurement_context']['species']['value'],'Danio rerio (zebrafish)')
            self.assertTrue(seen['04_fresh_continuation']['memory']['retrieved'])
            self.assertEqual(len(pilot.hypotheses.current()), 3)
            incomplete = {'summary': '', 'artifacts': [], 'evidence': [], 'claims': [],
                          'limitations': [], 'next_actions': [], 'ideas': [], 'preserved_branches': []}
            with self.assertRaisesRegex(ValueError, 'each exact hypothesis ref'):
                pilot.validate('05_candidates', 'discussion_recorder', incomplete,
                               seen['05_candidates'], False, False)
            self.assertTrue(any('/hypothesis_state/' in p for p in
                                json.loads((pilot.run/'GENERATION_FREEZE.json').read_text())['files']))
            hypothesis_before = {str(p): digest(p) for p in pilot.hypotheses.root.rglob('*.json')}
            before = {str(p):digest(p) for p in pilot.memory.root.rglob('*.json')}
            with patch('fish_inquiry.invoke',side_effect=AssertionError('Must reuse accepted stages')), patch('final_evaluation.stage_run',side_effect=AssertionError('Must reuse final check')):
                InquiryPilot(case,30,'test',config,fetch).execute()
            self.assertEqual(before,{str(p):digest(p) for p in pilot.memory.root.rglob('*.json')})
            self.assertEqual(hypothesis_before, {str(p): digest(p) for p in pilot.hypotheses.root.rglob('*.json')})


if __name__ == '__main__':
    unittest.main()
