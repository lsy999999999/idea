"""Regression cases found by reviewing failure and post-learning paths."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import run_ours as runner
from hypothesis_rounds import run_rounds
from learning_support import LearningServices
from research_tools import ResearchTools
from research_context import ContextStore, dumps
import test_hypothesis_strategy as strategy
from test_hypothesis_strategy import write


class SelfReviewTests(unittest.TestCase):
    def test_post_learning_move_and_history_drive_next_turn(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            seen = []
            def call(sid, owner, prompt, packet, outputs):
                seen.append((owner, packet))
                result = {'development_step': {'work': 'Develop relation'},
                          'next_research_move': {'action': 'finish', 'operation': 'hold',
                                                'focus': 'relation', 'reason': 'Earlier decision'}}
                if packet['progress_comparison']:
                    result['progress_review'] = {**packet['progress_comparison'], 'kind': 'advance', 'reason': 'Learning changed the relation'}
                path = root / (sid + '.json'); write(path, result)
                return path, result
            def learn(sid, owner, path, outputs):
                if sid.endswith('001'): return {'outputs': [], 'history': []}
                learned = json.loads(path.read_text())
                learned['next_research_move'].update(action='develop', operation='derive', owner='b', reason='New material enables continuation')
                p = root / (sid + '_learn_0.json'); write(p, learned)
                return {'outputs': [p], 'history': [(sid + '_learn_0', owner, p)]}
            run_rounds(root, [('a', 'optics'), ('b', 'optics')], [], call, learn, lambda *a: None, rounds=2)
            self.assertEqual([r[0] for r in seen], ['a', 'b'])
            self.assertEqual(seen[1][1]['progress_comparison']['after_stage'], '09_develop_000_learn_0')
            events = json.loads((root / 'research_rounds/events.json').read_text())
            self.assertTrue(events[0]['decision_source'].endswith('_learn_0.json'))

    def test_invalid_semantic_result_is_repaired_before_cache(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = runner.StageAdapter.__new__(runner.StageAdapter)
            adapter.root, adapter.case, adapter.cfg = Path(td), 'optical', {'model': 'fake'}
            adapter.api = adapter.definition_api = object()
            good = {'assessments': [{'source_id': 'K1', 'relation': 'method', 'reason': 'Useful', 'quote': 'A weighted sum'}]}
            adapter.model = Mock(side_effect=[{'content': '{}'}, {'content': json.dumps(good)}])
            result = adapter.assess_learning({'gap': 'weights'}, [{'id': 'K1', 'text': 'A weighted sum'}], [])
            self.assertEqual(result, good)
            self.assertEqual(adapter.model.call_count, 2)
            self.assertEqual(adapter.assess_learning({'gap': 'weights'}, [{'id': 'K1', 'text': 'A weighted sum'}], []), good)
            self.assertEqual(adapter.model.call_count, 2)

    def test_finish_waits_for_service_only_tail_to_reach_peer(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); seen = []
            tail = root / 'service_reply.json'; write(tail, {'status': 'returned', 'case_facts': []})
            def call(sid, owner, prompt, packet, outputs):
                seen.append(owner)
                if len(seen)==2:self.assertIn(tail, outputs)
                result={'development_step':{'work':'Specific remaining obstacle'},
                        'next_research_move':{'action':'finish','operation':'hold','focus':'relation','reason':'No useful next move'}}
                path=root/(sid+'.json');write(path,result);return path,result
            def learn(sid,*args):
                return {'outputs':[tail] if sid.endswith('000') else [],'history':[]}
            run_rounds(root,[('a','optics'),('b','optics')],[],call,learn,lambda *a:None,rounds=2)
            self.assertEqual(seen,['a','b'])
            status=json.loads((root/'research_rounds/status.json').read_text())
            self.assertEqual(status['status'],'finished')
            self.assertEqual(status['pending_service'],[])

    def test_invalid_existing_service_cache_is_preserved_and_recovered(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = runner.StageAdapter.__new__(runner.StageAdapter)
            adapter.root, adapter.case, adapter.cfg = Path(td), 'optical', {'model': 'fake'}
            adapter.api = adapter.definition_api = object()
            packet = {'instruction': 'check', 'payload': {}, 'model': 'fake', 'effort': None, 'version': runner.VERSION}
            key = hashlib.sha256(dumps(packet).encode()).hexdigest()
            path = Path(td) / 'controller_only/optical/service_calls/definition_reviewer' / (key + '.json')
            write(path, {'packet': packet, 'result': {'supported': 'true'}})
            good = {'question_is_neutral': True, 'answer_is_neutral': True, 'supported': True}
            adapter.model = Mock(return_value={'content': json.dumps(good)})
            self.assertEqual(adapter.semantic_json('definition_reviewer', 'check', {}), good)
            self.assertEqual(len(list(path.parent.glob('*.rejected*.json'))), 1)
            self.assertEqual(adapter.model.call_count, 1)

    def test_definition_tool_can_retry_after_transient_service_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = {'status': 'unknown', 'facts': []}
            definitions = SimpleNamespace(request=Mock(side_effect=[ValueError('Service temporarily unavailable'), result, result]))
            tool = ResearchTools(ContextStore(root / 'docs'), root / 'stage', {}, definitions=definitions)
            self.assertEqual(tool.call('request_case_definition', {'question': 'Scale?'}, 'first')['status'], 'error')
            self.assertEqual(tool.call('request_case_definition', {'question': 'Scale?'}, 'retry')['status'], 'unknown')
            self.assertEqual(tool.call('request_case_definition', {'question': 'Scale?'}, 'again')['status'], 'unknown')
            self.assertTrue(tool.events[-1]['cached'])
            self.assertEqual(len(list(tool.directory.glob('failed_attempts/*.json'))), 1)

    def test_cached_learning_reply_rechecks_definition_basis(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            definitions = strategy.DisclosureTests().service(root, lambda *a: {'status': 'unknown', 'facts': []})
            service = LearningServices(root / 'run', definitions=definitions)
            request = {'learning_request': {'needed': False, 'case_questions': ['Scale?']}}
            service.reply('s', request)
            next(definitions.public.glob('*.json')).write_text('{}')
            with self.assertRaisesRegex(ValueError, 'modified'):
                service.reply('s', request)

    def test_first_freeze_rejects_changed_registered_raw_original(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            service = strategy.DisclosureTests().service(root, lambda *a: {'status': 'unknown', 'facts': []})
            raw = root / 'controller_only/raw.html'; raw.write_text('<p>Original</p>')
            registry = json.loads(service.registry.read_text())
            registry['documents'][0].update(original_path=str(raw), original_sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
            write(service.registry, registry)
            service.request('Scale?')
            raw.write_text('<p>Changed</p>')
            with self.assertRaisesRegex(ValueError, 'changed'):
                service.freeze_evidence()


if __name__ == '__main__': unittest.main()
