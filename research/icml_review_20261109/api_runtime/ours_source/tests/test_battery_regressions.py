"""Contract regressions observed in the real battery scene, not scientific-quality tests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from learning_support import LearningServices, service_request
from discover import read
from portfolio_contracts import validate_developer


class BatteryContractRegressions(unittest.TestCase):
    def test_declined_analysis_placeholder_does_not_create_a_pending_task(self):
        answer = {'analysis_plan': {'needed': False, 'reason': 'No calculation requested'}}
        before = copy.deepcopy(answer)
        request, routing = service_request(answer)
        self.assertFalse(request['needed'])
        self.assertEqual(request['operations'], [])
        self.assertFalse(routing['knowledge_requested'])
        self.assertEqual(answer, before)
        with tempfile.TemporaryDirectory() as folder:
            service = LearningServices(folder, fetch=lambda url: self.fail('No search requested'))
            self.assertIsNone(service.reply('no_operation', answer))

    def test_real_analysis_still_routes_when_needed_is_false(self):
        plan = {'needed': False, 'kind': 'calculation', 'expression': 'sum(x)',
                'bindings': {'x': [1, 2]}}
        request, routing = service_request({'learning_request': {'needed': False},
                                            'analysis_plan': plan})
        self.assertTrue(request['needed'])
        self.assertEqual(request['operations'], [plan])
        self.assertFalse(routing['knowledge_requested'])
        with tempfile.TemporaryDirectory() as folder:
            service = LearningServices(folder, fetch=lambda url: self.fail('No search requested'))
            reply = read(service.reply('real_operation', {'analysis_plan': plan}))
            self.assertEqual(reply['computed'][0]['result']['status'], 'executed')
            self.assertEqual(reply['computed'][0]['result']['actual'], 3)

    @staticmethod
    def packet():
        # learning_lab supplies immutable files as path/text wrappers, not flat sources.
        return {'direction': {'id': 'D001'},
            'hypothesis_state': {'self': [], 'peer_branches': []},
            'feedback': {'suggestions': []},
            'common': [{'path': '/snapshot/source_catalog.json', 'text': json.dumps({
                'source_result': '/snapshot/materials/result.json',
                'sources': [{'id': 'S1'}, {'id': 'S2'}]})}],
            'service_replies': [{'sources': [{'id': 'K1'}]}],
            'memory': {'available_index': {}}}

    @staticmethod
    def result(ids):
        return {'hypothesis_updates': [], 'feedback_responses': [],
            'source_use': [{'source_id': sid, 'relation': 'not_read',
                            'reason': 'Supplied source not studied'} for sid in ids]}

    def test_nested_common_catalog_is_accepted_with_mandatory_service_source(self):
        validate_developer(self.result(['K1', 'S1', 'S2']), self.packet())
        validate_developer(self.result(['K1']), self.packet())

    def test_nested_support_does_not_allow_unknown_duplicate_or_missing_service_ids(self):
        for ids in (['K1', 'invented'], ['K1', 'K1'], ['S1']):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                validate_developer(self.result(ids), self.packet())


if __name__ == '__main__':
    unittest.main()
