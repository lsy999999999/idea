"""General entry regressions motivated by the wine trial; actors are fixtures."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import learning_lab as lab
from discover import PROJECT, read, write
from learning_memory import Memory, digest
from learning_support import (material_coverage, calculation, LearningServices, review_packet,
                              audit_review, validate_uptake)
from import_learning_handoff import main as import_native
sys.path.insert(0, str(PROJECT/'bootstrap'))
from novelty_fixtures import claim_report


def base():
    return {'summary': 'Synthetic test result', 'artifacts': ['result.json'],
            'evidence': [], 'claims': [], 'limitations': [], 'next_actions': []}


def note(**kwargs):
    return {'key': 'example_relation', 'title': 'Relation', 'kind': 'hypothesis', 'mastery': 'explained',
            'understanding': 'Provisional relation', 'conditions': 'Illustrative only',
            'example': 'A=(6,5), B=(8,7), rater 2 is +2', 'open_questions': 'Consequences?',
            'tags': ['wine'], 'sources': [], 'revision_reason': 'Develop the relation', **kwargs}


def hypothesis():
    return {'key': 'relation', 'base_version': 0, 'assumption': 'A provisional domain relation',
            'motivation': 'A specific unexplained contrast', 'conceptual_move': None,
            'implications': [], 'open_questions': [], 'status': 'developing',
            'reason': 'Explore the contrast', 'influenced_by': []}


class SupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=PROJECT/'tests')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_metadata_and_duplicate_documentation_do_not_meet_material_contract(self):
        path = self.root/'source.txt'; path.write_text('Exact source observation')
        source = {'id': 'a', 'url': 'https://example.org/a', 'local_path': str(path),
                  'source_kind': 'original_study', 'content_access': 'metadata',
                  'domain_relation': 'direct', 'relevance_reason': 'Domain relation',
                  'supporting_quote': 'Exact source observation'}
        self.assertEqual(material_coverage({'sources': [source]})['status'], 'incomplete')
        source['content_access'] = 'abstract'
        review = {**source, 'id': 'b', 'source_kind': 'review'}
        self.assertIn('independent_domain_foundation', material_coverage({'sources': [source, review]})['missing'])
        other = self.root/'review.txt'; other.write_text('Independent domain foundation')
        review.update(url='https://example.org/b', local_path=str(other), supporting_quote=other.read_text())
        self.assertEqual(material_coverage({'sources': [source, review]})['status'], 'covered')

    def test_wine_arithmetic_and_axis_meaning_are_distinct(self):
        bindings = {'ratings': [[6, 5], [8, 7]]}
        wrong = calculation({'kind': 'calculation', 'bindings': bindings,
                             'expression': 'ratings[:,1]-ratings[:,0]', 'expected': [2, 2]})
        self.assertEqual(wrong['actual'], [-1, -1])
        self.assertFalse(wrong['matches_expected'])
        right = calculation({'kind': 'calculation', 'bindings': bindings,
                             'expression': 'ratings[1,:]-ratings[0,:]', 'expected': [2, 2]})
        self.assertTrue(right['matches_expected'])
        for expression in ('__import__("os")', 'ratings.__class__', 'ratings+ratings[:1,:1,:1]'):
            self.assertEqual(calculation({'kind': 'calculation', 'bindings': bindings,
                                         'expression': expression})['status'], 'pending_controller')

    def test_reviewer_quote_provenance_and_correction_required(self):
        source = self.root/'result.json'; write(source, {**base(), 'memory_notes': [note()]})
        packet = review_packet({'learn_A': ('A', source)})
        finding = {'id': 'E1', 'source_stage': 'learn_A', 'quote': note()['example'],
                   'kind': 'arithmetic', 'status': 'needs_correction', 'reason': 'Rater difference is -1',
                   'note_keys': ['example_relation'], 'calculation': {'bindings': {'r': [[6,5],[8,7]]},
                   'expression': 'r[:,1]-r[:,0]', 'expected': [2,2]}}
        report = audit_review({'findings': [finding]}, packet)
        self.assertEqual(report['findings'][0]['recomputation']['actual'], [-1,-1])
        self.assertEqual(report['findings'][0]['owner'], 'A')
        response = {'verification_responses': [{'finding_id': 'E1', 'stance': 'accept', 'reason': 'Correct example'}]}
        with self.assertRaisesRegex(ValueError, 'same-key'):
            validate_uptake(response, report, 'A')
        validate_uptake({**response, 'memory_notes': [note(kind='correction',example='Rater difference is -1')]}, report, 'A')
        with self.assertRaisesRegex(ValueError, 'quote'):
            audit_review({'findings': [{**finding, 'quote': 'Invented source'}]}, packet)
        finding.pop('calculation')
        self.assertEqual(audit_review({'findings': [finding]}, packet)['findings'][0]['status'], 'undetermined')

    def test_controller_retrieval_retries_failed_attempt_without_overwriting_it(self):
        calls = []
        def fetch(url):
            calls.append(url)
            if len(calls) <= 3:
                raise OSError('temporary DNS failure')
            return json.dumps({'resultList': {'result': [{'title': 'Actual domain source',
                'firstPublicationDate': '2001-01-01', 'abstractText': 'A readable source.'}]}})
        service = LearningServices(self.root, fetch=fetch)
        request = {'learning_request': {'needed': True, 'search_terms': ['domain relation']}}
        reply = service.reply('one', request)
        self.assertEqual(len(read(reply)['knowledge_attempts']), 2)
        self.assertTrue(read(reply)['sources'])
        count = len(calls)
        self.assertEqual(service.reply('one', request), reply)
        self.assertEqual(len(calls), count)
        self.assertTrue(list((self.root/'services/knowledge/controller_only/one_search_0').glob('*.json')))
        sid = read(reply)['sources'][0]['id']
        again = read(service.reply('reread', {'learning_request': {'needed': True, 'source_ids': [sid]}}))
        self.assertEqual(again['sources'][0]['id'], sid)
        self.assertEqual(len(calls), count)

    def test_top_level_calculation_returns_result_without_search(self):
        service = LearningServices(self.root, fetch=lambda _: self.fail('No search requested'))
        reply = read(service.reply('calc', {'analysis_plan': {'kind': 'calculation',
                     'question': 'Rater contrast', 'bindings': {'a': [6,5]}, 'expression': 'a[1]-a[0]'}}))
        self.assertEqual(reply['computed'][0]['result']['actual'], -1)
        self.assertEqual(reply['knowledge_status'], 'not_requested')

    def test_failed_retrieval_remains_unresolved_after_bounded_retry(self):
        calls = []
        def fail(url):
            calls.append(url)
            raise OSError('DNS remains unavailable')
        service = LearningServices(self.root, fetch=fail)
        path = service.reply('offline', {'learning_request': {'needed': True, 'queries': ['specific relation']}})
        self.assertEqual(len(calls), 6)  # Three providers, two separately recorded attempts.
        self.assertEqual(read(path)['knowledge_status'], 'unresolved')
        self.assertEqual(read(path)['sources'], [])


class GeneralPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=PROJECT/'tests')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lab = self.root/'lab'; (self.lab/'scenarios').mkdir(parents=True)
        (self.lab/'scenarios/wine.md').write_text('Wine domain relations. No feasibility gate.')
        (self.lab/'PLAN_SOURCE.md').write_text('Preserve independent disciplinary learning.')
        self.run = self.root/'run'
        self.memory = Memory(self.root/'memory')
        self.args = SimpleNamespace(model='gpt-6-luna', effort='low', timeout=10, check_timeout=10,
                                    executor='cli', knowledge_fetch=lambda _: self.fail('Unexpected search'))
        self.seen = []

    def fake(self, run, stage, role, prompt, inputs, model, effort, timeout):
        self.seen.append(stage)
        workspace = run/'stages'/stage/'workspace'; workspace.mkdir(parents=True, exist_ok=True)
        result = base()
        contexts = [read(p) for p in inputs if p.parent.name == 'researcher_context']
        if contexts:
            c = contexts[0]
            from cycle_fixture import development_step
            result['development_step'] = development_step(c['development_cycle'])
            self.assertIn('HYPOTHESIS DEVELOPMENT', prompt)
            self.assertNotIn('question_before, question_after', prompt)
            if stage.startswith('02_initial_') and '_learn_' not in stage:
                result['initial_question'] = 'Original question of '+role
                result['hypothesis_updates'] = [hypothesis()]
                self.assertEqual(c['hypothesis_state']['peer_branches'], [])
                result['memory_notes'] = [note()]
            else:
                current = c['question_state']['self']
                result['personal_question_update'] = {'base': current['ref'], 'action': 'retain',
                    'question': current['question'], 'reason': 'Retain own line', 'influenced_by': []}
                result['shared_question_update'] = None
                result['memory_notes'] = []
            result['learning_request'] = {'needed': False}
            if stage == '03_exchange_0':
                result['analysis_plan'] = {'kind': 'calculation', 'question': 'Rater contrast',
                    'bindings': {'r': [[6,5],[8,7]]}, 'expression': 'r[:,1]-r[:,0]', 'expected': [2,2]}
            if stage.startswith('05_return_'):
                report = read(run/'internal_review/report.json')
                result['verification_responses'] = [{'finding_id': f['id'], 'stance': 'accept',
                                                     'reason': 'The rater difference is -1'} for f in report['findings']]
                if stage == '05_return_0':
                    result['memory_notes'] = [note(kind='correction', example='Rater contrast is -1; sample contrast is +2',
                                                  sources=[str(run/'internal_review/report.json')])]
            if stage == '08_fresh_continuation':
                self.assertNotIn('07_check', self.seen)
                self.assertTrue(c['hypothesis_state']['self'])
                packet = read(run/'memory_retrieval/fresh_continuation.json')
                self.assertFalse(any(n['note']['source_stage'] == '07_check_experience' for n in packet['retrieved']))
        elif stage == '08_fresh_continuation':
            self.assertFalse(contexts)
            self.assertEqual([p.name for p in inputs], ['wine.md','IDEA_CHECK.md','PLAN_SOURCE.md','fresh_continuation.json'])
            self.assertFalse(any('/researcher_context/' in str(p) for p in inputs))
            packet=read(run/'memory_retrieval/fresh_continuation.json')
            self.assertFalse(any(n['note']['source_stage']=='07_check_experience' for n in packet['retrieved']))
        elif stage.startswith('01_materials'):
            original = workspace/'study.txt'; original.write_text('Observed a concrete domain relation')
            review = workspace/'foundation.txt'; review.write_text('An independent domain foundation')
            result.update(materials=[{'observation': 'Domain observation'}], sources=[
                {'id': str(i), 'title': kind, 'url': 'https://example.org/'+kind,
                 'local_path': str(p), 'content_access': 'abstract', 'source_kind': kind,
                 'domain_relation': 'direct', 'relevance_reason': 'Explains the situation',
                 'supporting_quote': p.read_text()} for i, (p, kind) in enumerate(
                     [(original, 'original_study'), (review, 'review')])])
        elif stage == '04_internal_review':
            result['findings'] = [{'id': 'E1', 'source_stage': '02_initial_0',
                'quote': note()['example'], 'kind': 'arithmetic', 'status': 'needs_correction',
                'reason': 'Rater/sample axes confused', 'note_keys': ['example_relation'],
                'calculation': {'bindings': {'r': [[6,5],[8,7]]}, 'expression': 'r[:,1]-r[:,0]', 'expected': [2,2]}}]
        elif stage == '06_candidates':
            history = read(run/'candidate_history.json')
            result['ideas'] = [{'id': 'W', 'title': 'Unfinished domain relation', 'idea': 'A provisional relation'}]
            result['preserved_branches'] = [{'ref': h['ref'], 'reason': 'Retain unfinished branch'}
                                           for h in history['current_hypotheses']]
        elif stage == '07_check':
            self.assertTrue((run/'GENERATION_FREEZE.json').exists())
            result = claim_report(read(run/'ideas.json')['ideas'], workspace/'evidence')
        else:
            self.fail('Unexpected stage '+stage)
        path = workspace/'result.json'; write(path, result)
        return path, result

    def test_full_generation_correction_freeze_isolation_and_restart(self):
        # Preserve a historical evaluation note, but do not feed it into generation.
        rid = lab.CASES['wine'][1][0]
        old = self.root/'old.json'; write(old, {'memory_notes': [note(key='wine_research_experience')]})
        self.memory.commit(rid, 'old', '07_check_experience', old)
        with patch.object(lab, 'LAB', self.lab), patch.object(lab, 'stage_run', side_effect=self.fake):
            lab.run_case('wine', self.run, self.args, self.memory)
        self.assertEqual(self.seen[-1], '07_check')
        self.assertLess(self.seen.index('08_fresh_continuation'), self.seen.index('06_candidates'))
        first = read(self.run/'researcher_context/02_initial_0.json')['development_cycle']
        self.assertEqual(first['previous_steps'], [])
        self.assertEqual(first['peer_sources'], [])
        exchange = read(self.run/'researcher_context/03_exchange_0.json')['development_cycle']
        self.assertTrue(exchange['previous_steps'])
        self.assertTrue(exchange['peer_sources'])
        self.assertFalse((self.run/'researcher_context/08_fresh_continuation.json').exists())
        self.assertFalse(read(self.run/'CONTINUATION_SCOPE.json')['state_context_injected'])
        idx = self.memory.index(lab.CASES['wine'][0][0])
        revised = read(idx['notes']['example_relation']['path'])
        self.assertEqual(revised['kind'], 'correction')
        self.assertEqual(revised['version'], 2)
        self.assertTrue(Path(revised['supersedes']).exists())
        self.assertFalse((self.run/'research_experience.json').exists())
        snapshot = {str(p): digest(p) for p in self.memory.root.rglob('*.json')}
        with patch.object(lab, 'LAB', self.lab), patch.object(lab, 'stage_run', side_effect=AssertionError('Replay must reuse')):
            lab.run_case('wine', self.run, self.args, self.memory)
        self.assertEqual(snapshot, {str(p): digest(p) for p in self.memory.root.rglob('*.json')})
        self.assertTrue(read(self.run/'EVALUATION_ISOLATION.json')['memory_unchanged'])

    def test_general_entry_runs_development_before_terminal_freeze(self):
        from portfolio_runtime import BatchRuntime, PendingRoles
        from test_portfolio import fixture
        self.args.development_periods = 1
        self.args.development_slots = 2
        self.args.development_budget = 23
        self.args.executor = 'cli'
        original = BatchRuntime.batch
        def auto_batch(runtime, bid, jobs):
            runtime.executor = 'queue'
            try:
                return original(runtime, bid, jobs)
            except PendingRoles:
                for name in read(runtime.root/'PENDING_ROLES.json')['requests']:
                    req = read(name)
                    packet = read(req['input'])
                    if req['kind'] == 'ranker':
                        from test_portfolio import ranking
                        adapted = copy.deepcopy(packet)
                        for d in adapted['directions']:
                            d['seed']['assumption'] = d['seed']['idea']
                        value = ranking(adapted)
                    else:
                        value = fixture(req)
                    ws = Path(req['workspace'])
                    (ws/'NOTE.md').write_text('Fixture artifact')
                    write(ws/'result.json', value)
                    runtime.deliver(req['stage'], 'fixture')
                return original(runtime, bid, jobs)
        with patch.object(lab, 'LAB', self.lab), patch.object(lab, 'stage_run', side_effect=self.fake), \
             patch.object(BatchRuntime, 'batch', auto_batch):
            lab.run_case('wine', self.run, self.args, self.memory)
        self.assertTrue((self.run/'development/STOP.json').exists())
        self.assertTrue(any('/development/' in p for p in read(self.run/'GENERATION_FREEZE.json')['files']))
        self.assertTrue(read(self.run/'EVALUATION_ISOLATION.json')['memory_unchanged'])

    def test_queue_initializes_manifest_and_preserves_input_identity_on_import(self):
        self.args.executor = 'queue'
        with patch.object(lab, 'LAB', self.lab), self.assertRaises(SystemExit) as exit:
            lab.run_case('wine', self.run, self.args, self.memory)
        self.assertEqual(exit.exception.code, 75)
        request = read(self.run/'PENDING_NATIVE.json')
        self.assertTrue((self.run/'manifest.json').exists())
        from runtime import load_manifest
        runtime_manifest = load_manifest(self.run/'manifest.json', self.run.name, 'gpt-6-luna', 'low')
        self.assertEqual(runtime_manifest['run_id'], self.run.name)
        # Deliver a fixture through the real native importer, then resume the next stage.
        args = (self.run, request['stage'], request['role'], request['prompt'],
                [Path(p) for p in request['inputs']], 'gpt-6-luna', 'low', 10)
        path, result = self.fake(*args)
        write(Path(request['workspace'])/'result.json', result)
        with patch.object(sys, 'argv', ['import', '--run', str(self.run), '--agent', 'fixture']):
            import_native()
        self.assertEqual(read(self.run/'learning_state.json')['stages']['01_materials']['input_sha256'], request['input_sha256'])
        with patch.object(lab, 'LAB', self.lab), self.assertRaises(SystemExit):
            lab.run_case('wine', self.run, self.args, self.memory)
        self.assertEqual(read(self.run/'PENDING_NATIVE.json')['stage'], '02_initial_0')
        request = read(self.run/'PENDING_NATIVE.json')
        args = (self.run, request['stage'], request['role'], request['prompt'],
                [Path(p) for p in request['inputs']], 'gpt-6-luna', 'low', 10)
        _, result = self.fake(*args)
        result.pop('development_step')
        write(Path(request['workspace'])/'result.json', result)
        with patch.object(sys, 'argv', ['import', '--run', str(self.run), '--agent', 'fixture']):
            with self.assertRaisesRegex(ValueError, 'development_step'):
                import_native()
        self.assertNotIn('02_initial_0', read(self.run/'learning_state.json')['stages'])
        self.assertTrue((self.run/'PENDING_NATIVE.json').exists())

    def test_cli_failure_automatically_queues_without_auth_retry(self):
        with patch.object(lab, 'LAB', self.lab), patch.object(lab, 'stage_run', side_effect=RuntimeError('401')) as runner:
            with self.assertRaises(SystemExit):
                lab.run_case('wine', self.run, self.args, self.memory)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(read(self.run/'PENDING_NATIVE.json')['fallback_reason'], 'cli_failed_inspect_runtime_manifest')

    def test_changed_settings_cannot_resume_frozen_old_run(self):
        self.args.executor = 'queue'
        with patch.object(lab, 'LAB', self.lab), self.assertRaises(SystemExit):
            lab.run_case('wine', self.run, self.args, self.memory)
        self.args.model = 'different'
        with patch.object(lab, 'LAB', self.lab), self.assertRaisesRegex(ValueError, 'new run ID'):
            lab.run_case('wine', self.run, self.args, self.memory)

    def test_material_gap_triggers_targeted_recovery_before_researchers(self):
        def fake(*args):
            path, result = self.fake(*args)
            if args[1] == '01_materials':
                for s in result['sources']:
                    s['content_access'] = 'metadata'
                write(path, result)
            return path, result
        with patch.object(lab, 'LAB', self.lab), patch.object(lab, 'stage_run', side_effect=fake):
            lab.run_case('wine', self.run, self.args, self.memory)
        self.assertLess(self.seen.index('01_materials_recovery'), self.seen.index('02_initial_0'))
        self.assertEqual(read(self.run/'MATERIAL_COVERAGE.json')['status'], 'covered')

    def test_peer_question_cannot_be_admitted_as_own_previous_question(self):
        def fake(*args):
            path, result = self.fake(*args)
            if args[1] == '03_exchange_1':
                result['question_before'] = 'Original question of '+lab.CASES['wine'][0][0]
                write(path, result)
            return path, result
        with patch.object(lab, 'LAB', self.lab), patch.object(lab, 'stage_run', side_effect=fake):
            with self.assertRaisesRegex(ValueError, 'before/after'):
                lab.run_case('wine', self.run, self.args, self.memory)
        self.assertNotIn('03_exchange_1', read(self.run/'learning_state.json')['stages'])

    def test_restart_after_hypothesis_commit_does_not_regenerate_accepted_role(self):
        from learning_support import HypothesisState
        original = HypothesisState.accept
        interrupted = []
        def fail_after_commit(instance, stage, *args, **kwargs):
            result = original(instance, stage, *args, **kwargs)
            if stage == '02_initial_0' and not interrupted:
                interrupted.append(stage)
                raise OSError('Interrupted after event commit')
            return result
        # The external runner itself caches its completed stage result before controller admission.
        outputs = {}
        def cached(*args):
            if args[1] not in outputs:
                outputs[args[1]] = self.fake(*args)
            return outputs[args[1]]
        with patch.object(lab, 'LAB', self.lab), patch.object(lab, 'stage_run', side_effect=cached):
            with patch.object(HypothesisState, 'accept', fail_after_commit), self.assertRaises(OSError):
                lab.run_case('wine', self.run, self.args, self.memory)
            lab.run_case('wine', self.run, self.args, self.memory)
        self.assertEqual(self.seen.count('02_initial_0'), 1)

    def test_invalid_memory_is_rejected_before_question_and_hypothesis_commit(self):
        def fake(*args):
            path,result=self.fake(*args)
            if args[1]=='02_initial_0':
                result['memory_notes'][0]['kind']='invented_kind';write(path,result)
            return path,result
        with patch.object(lab,'LAB',self.lab),patch.object(lab,'stage_run',side_effect=fake):
            with self.assertRaisesRegex(ValueError,'knowledge kind'):
                lab.run_case('wine',self.run,self.args,self.memory)
        self.assertNotIn('02_initial_0',read(self.run/'learning_state.json')['stages'])
        self.assertFalse(list((self.run/'hypothesis_state/events').glob('*.json')))
        self.assertFalse(list((self.run/'question_state/events').glob('*.json')))

    def test_final_check_memory_mutation_is_detected(self):
        def fake(*args):
            path, result = self.fake(*args)
            if args[1] == '07_check':
                write(self.memory.root/'unauthorized.json', {'changed': True})
            return path, result
        with patch.object(lab, 'LAB', self.lab), patch.object(lab, 'stage_run', side_effect=fake):
            with self.assertRaisesRegex(ValueError, 'modified memory'):
                lab.run_case('wine', self.run, self.args, self.memory)


if __name__ == '__main__':
    unittest.main()
