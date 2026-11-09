"""Regressions for missing conceptual handoffs; scientific actors are fixtures."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from discover import read
from hypothesis_cycle import context, validate_step, portfolio_context
from learning_support import LearningServices
from cycle_fixture import development_step


class CycleTests(unittest.TestCase):
    def setUp(self):
        self.ctx = context({'seed': 'A condition might change a process',
                            'peer:A': 'The process could depend on its history',
                            'service:A': {'sources': [], 'knowledge_status': 'unresolved'}},
                           peer_sources=['peer:A'], service_sources=['service:A'])
        self.result = {'development_step': development_step(self.ctx), 'hypothesis_updates': []}

    def test_unfinished_hypothesis_and_failed_learning_are_valid(self):
        validate_step(self.result, self.ctx)
        self.assertEqual(self.result['hypothesis_updates'], [])

    def test_unread_service_and_generic_peer_agreement_cannot_skip_uptake(self):
        for missing in ('peer:A', 'service:A'):
            result = copy.deepcopy(self.result)
            result['development_step']['uptake'] = [r for r in result['development_step']['uptake']
                                                    if r['source'] != missing]
            with self.assertRaises(ValueError):
                validate_step(result, self.ctx)

    def test_fabricated_or_cross_source_quote_rejected(self):
        result = copy.deepcopy(self.result)
        result['development_step']['focus']['source'] = 'peer:A'
        with self.assertRaisesRegex(ValueError, 'focus'):
            validate_step(result, self.ctx)
        result = copy.deepcopy(self.result)
        row = result['development_step']['uptake'][0]
        row.update(effect='revise', quote='Reading succeeded')
        with self.assertRaisesRegex(ValueError, 'quote'):
            validate_step(result, self.ctx)

    def test_retrieval_must_target_the_declared_gap(self):
        self.result['learning_request'] = {'needed': True, 'gap': 'Broad unrelated topic', 'why_now': 'Survey'}
        with self.assertRaisesRegex(ValueError, 'Learning request'):
            validate_step(self.result, self.ctx)
        step = self.result['development_step']
        self.result['learning_request'].update(gap=step['gap'], why_now=step['reason'])
        validate_step(self.result, self.ctx)

    def test_claimed_relation_requires_retained_hypothesis(self):
        self.result['development_step']['outcome'].update(kind='relation', statement='A changes B')
        with self.assertRaisesRegex(ValueError, 'hypothesis update'):
            validate_step(self.result, self.ctx)
        self.result['hypothesis_updates'] = [{'assumption': 'A changes B', 'implications': []}]
        validate_step(self.result, self.ctx)

    def test_own_gap_survives_resume_and_peers_do_not_count_as_own_stagnation(self):
        step = self.result['development_step']
        history = [{'stage': s, 'owner': o, 'development_step': step}
                   for s, o in [('a0', 'A'), ('b0', 'B'), ('a1', 'A')]]
        packet = {'direction': {'id': 'D001', 'development_history': history},
                  'hypothesis_state': {'self': []}, 'peer_drafts': [], 'service_replies': []}
        a = portfolio_context(packet, 'A'); b = portfolio_context(packet, 'B')
        self.assertTrue(a['repeated_no_change'])
        self.assertFalse(b['repeated_no_change'])
        self.assertEqual([r['stage'] for r in a['previous_steps']], ['a0', 'a1'])
        self.assertEqual(a['previous_steps'][-1]['step']['gap'], step['gap'])
        self.assertEqual(a, portfolio_context(copy.deepcopy(packet), 'A'))

    def test_service_retains_reason_and_rejects_changed_hypothesis_on_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            def fail(_):
                raise OSError('Fixture network failure')
            service = LearningServices(directory, fetch=fail)
            step = self.result['development_step']
            answer = {'development_step': step, 'learning_request': {'needed': True,
                      'gap': step['gap'], 'why_now': step['reason'], 'queries': ['specific connection']}}
            path = service.reply('learning_A', answer)
            reply = read(path)
            self.assertEqual(reply['development_context'], step)
            self.assertEqual(reply['request_stage'], 'learning_A')
            self.assertEqual(reply['knowledge_status'], 'unresolved')
            self.assertEqual(path, service.reply('learning_A', answer))
            changed = copy.deepcopy(answer)
            changed['development_step']['gap'] = 'Another gap'
            with self.assertRaisesRegex(ValueError, 'changed'):
                service.reply('learning_A', changed)


if __name__ == '__main__':
    unittest.main()
