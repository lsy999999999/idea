"""Explicit analyses must reach the executor and return to their researcher."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from fish_inquiry import InquiryPilot, service_request
from fish_materials import CASE
from inquiry_services import InquiryBroker
from prepare import HERE, save

CONFIG = json.loads((HERE/'configs/fish_v2.json').read_text())


def plan(expression='mean(positions)', **changes):
    return {'kind': 'analysis', 'record_id': 'R01', 'question': 'Describe supplied coordinates',
            'start': 0, 'stop': 20, 'outputs': [{'name': 'value', 'expression': expression}], **changes}


class RequestRoutingTests(unittest.TestCase):
    def test_top_level_runs_without_learning_flag_and_preserves_original(self):
        for learning in (None, {'needed': False}, {'needed': True, 'queries': ['foundation']}):
            answer = {'analysis_plan': plan()}
            if learning is not None:
                answer['learning_request'] = learning
            before = copy.deepcopy(answer)
            request, route = service_request(answer)
            self.assertTrue(request['needed'])
            self.assertEqual(request['operations'], [plan()])
            self.assertEqual(route['routes'][0]['field'], 'analysis_plan')
            self.assertEqual(answer, before)

    def test_merge_deduplicates_exact_plans_but_keeps_distinct_ones(self):
        other = plan('std(positions)')
        request, route = service_request({'learning_request': {'needed': True, 'operations': [plan()]},
                                          'analysis_plan': [plan(), other]})
        self.assertEqual(request['operations'], [plan(), other])
        self.assertEqual([r['operation_index'] for r in route['routes']], [0, 0, 1])
        self.assertEqual([r['deduplicated'] for r in route['routes']], [False, True, False])

    def test_false_learning_flag_does_not_suppress_operations_or_activate_search(self):
        request, _ = service_request({'learning_request': {'needed': False, 'operations': [plan()],
                                                          'queries': ['declined'], 'urls': ['declined'],
                                                          'knowledge': True, 'gap': 'old gap'}})
        self.assertTrue(request['needed'])
        self.assertEqual(request['queries'], [])
        self.assertEqual(request['urls'], [])
        self.assertNotIn('knowledge', request)
        for answer in ({}, {'analysis_plan': None}, {'analysis_plan': []},
                       {'learning_request': {'needed': False, 'queries': ['declined']}}):
            self.assertFalse(service_request(answer)[0]['needed'])

    def test_malformed_envelopes_are_not_silently_ignored(self):
        for answer in ({'analysis_plan': 'compute something'}, {'analysis_plan': [None]},
                       {'learning_request': {'needed': False, 'operations': [1]}},
                       {'learning_request': None}):
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                service_request(answer)


class ServiceDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pilot = InquiryPilot.__new__(InquiryPilot)
        self.pilot.run = Path(self.temp.name)
        self.pilot.config = {**CONFIG, 'max_request_hops': 2}
        self.pilot.broker = InquiryBroker(CASE, self.pilot.run/'services', CONFIG,
                                         fetch=Mock(side_effect=AssertionError('No search requested')))
        self.pilot.call = Mock(return_value={})

    def test_executes_once_and_returns_numeric_result_to_requester(self):
        answer = {'analysis_plan': plan(), 'learning_request': {'needed': False, 'operations': [plan()]}}
        with patch.object(self.pilot.broker.executor, 'run_plan', wraps=self.pilot.broker.executor.run_plan) as execute:
            learned = self.pilot.service('origin', 'animal_behaviorist', answer)
            self.pilot.service('origin', 'animal_behaviorist', answer)
            self.assertEqual(execute.call_count, 1)
        args = self.pilot.call.call_args.args
        self.assertEqual(args[:2], ('origin_learn_0', 'animal_behaviorist'))
        reply = args[3]['broker_reply']
        self.assertEqual(len(reply['computed']), 1)
        self.assertEqual(reply['computed'][0]['result']['status'], 'executed')
        actual = np.load(reply['computed'][0]['result']['full_outputs'])['output_0']
        positions, _ = self.pilot.broker.arrays('R01')
        np.testing.assert_allclose(actual, np.mean(positions[:20]), equal_nan=True)
        self.assertEqual(len(learned), 1)

    def test_new_plan_from_reply_and_final_budget_request_are_dispatched(self):
        self.pilot.config['max_request_hops'] = 1
        second = plan('std(positions)')
        self.pilot.call.return_value = {'analysis_plan': second, 'learning_request': {'needed': False}}
        learned = self.pilot.service('origin', 'animal_behaviorist', {'analysis_plan': plan()})
        self.assertEqual(len(learned), 2)
        self.assertEqual(learned[-1]['status'], 'read_return_pending_next_discussion')
        self.assertEqual(learned[-1]['continuation_material']['computed'][0]['request'], second)
        audit = json.loads((self.pilot.run/'request_dispatch/origin_continuation_request.json').read_text())
        self.assertEqual(audit['source_stage'], 'origin_learn_0')

    def test_bad_expression_alignment_and_missing_record_return_explicit_pending(self):
        for i, broken in enumerate((plan('unknown_function(positions)'),
                                   plan('positions[:,0,0]+diff(positions[:,0,0])'),
                                   plan(record_id=''))):
            with self.subTest(i=i):
                self.pilot.service('broken_'+str(i), 'animal_behaviorist', {'analysis_plan': broken})
                reply = self.pilot.call.call_args.args[3]['broker_reply']
                self.assertEqual(reply['computed'][0]['result']['status'], 'pending_controller')
                self.assertEqual(reply['controller_pending'][0]['request'], broken)
                self.assertTrue(reply['controller_pending'][0]['reason'])

    def test_interrupted_return_reuses_execution_and_rejects_changed_dispatch(self):
        answer = {'analysis_plan': plan()}
        self.pilot.call.side_effect = OSError('interrupted before researcher read')
        with self.assertRaises(OSError):
            self.pilot.service('origin', 'animal_behaviorist', answer)
        self.pilot.call.side_effect = None
        with patch.object(self.pilot.broker, 'request', side_effect=AssertionError('Do not execute twice')):
            self.pilot.service('origin', 'animal_behaviorist', answer)
        with self.assertRaisesRegex(ValueError, 'dispatch changed'):
            self.pilot.service('origin', 'animal_behaviorist', {'analysis_plan': plan('std(positions)')})
        path = self.pilot.run/'broker/origin_learn_0.json'
        reply = json.loads(path.read_text()); reply['request'] = {}
        save(path, reply)
        with self.assertRaisesRegex(ValueError, 'Cached broker request changed'):
            self.pilot.service('origin', 'animal_behaviorist', answer)


if __name__ == '__main__':
    unittest.main()
