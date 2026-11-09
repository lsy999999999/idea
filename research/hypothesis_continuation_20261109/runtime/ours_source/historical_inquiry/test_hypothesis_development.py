"""Hypothesis continuity, ownership and recovery; no live research claims."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from hypothesis_development import HypothesisState
from fish_inquiry import InquiryPilot


def card(key='line', base=0, **changes):
    return {'key': key, 'base_version': base, 'assumption': 'A provisional organizing relation',
            'motivation': 'Two descriptions leave a relation unexplained', 'conceptual_move': None,
            'implications': [], 'open_questions': ['Which distinction matters?'],
            'status': 'developing', 'reason': 'Explore the missing relation',
            'influenced_by': [], **changes}


class HypothesisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = HypothesisState(self.root/'hypotheses', ['A', 'B'])

    def accept(self, stage, owner='A', updates=None, packet=None):
        packet = packet if packet is not None else self.state.packet(stage, owner)
        result = {} if updates is None else {'hypothesis_updates': updates}
        path = self.root/(stage+'.json')
        path.write_text(json.dumps(result))
        return self.state.accept(stage, owner, result, path, packet)

    def test_incomplete_assumption_without_proof_data_or_feasibility_is_preserved(self):
        self.accept('initial', updates=[card()])
        self.accept('empty', updates=[])
        self.accept('legacy')
        self.assertEqual(len(self.state.current()), 1)
        self.assertIsNone(self.state.current()[0]['conceptual_move'])
        self.assertEqual(self.state.current()[0]['ref']['version'], 1)

    def test_owner_independence_and_initial_learning_visibility(self):
        self.accept('a', updates=[card()])
        self.assertEqual(self.state.packet('b_initial', 'B', True)['peer_branches'], [])
        self.accept('b', owner='B', updates=[card(assumption='A distinct explanation')])
        independent = self.state.packet('b_learn', 'B', True)
        self.assertEqual(len(independent['self']), 1)
        self.assertEqual(independent['peer_branches'], [])
        common = self.state.packet('b_exchange', 'B')
        self.assertEqual(common['peer_branches'][0]['ref']['owner'], 'A')
        bad = card(base=1, owner='A')
        with self.assertRaisesRegex(ValueError, 'ownership'):
            self.state.validate('b_exchange', 'B', {'hypothesis_updates': [bad]}, common)
        self.assertEqual(len(self.state.current()), 2)

    def test_alternative_and_park_resume_preserve_versions_and_influence(self):
        self.accept('initial', updates=[card()])
        parent = self.state.current()[0]['ref']
        self.accept('branch', updates=[card(base=1, status='parked'),
                                     card('alternative', influenced_by=[parent])])
        self.accept('resume', updates=[card(base=2, reason='A new conceptual route')])
        self.assertEqual([c['ref']['version'] for c in self.state.current()], [3, 1])
        self.assertEqual(self.state.current()[1]['influenced_by'], [parent])
        self.assertEqual(len(self.state.events()), 3)

    def test_stale_version_and_unseen_reference_rejected(self):
        self.accept('initial', updates=[card()])
        frozen = self.state.packet('stale', 'A')
        self.accept('revise', updates=[card(base=1, conceptual_move='Introduce a distinction')])
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.state.validate('stale', 'A', {'hypothesis_updates': [card(base=1)]}, frozen)
        packet = self.state.packet('unknown', 'A')
        with self.assertRaisesRegex(ValueError, 'supplied refs'):
            self.state.validate('unknown', 'A', {'hypothesis_updates': [card('other', influenced_by=[
                {'owner': 'B', 'key': 'unseen', 'version': 1}])]}, packet)

    def test_recovery_is_idempotent_and_packets_do_not_gain_future_context(self):
        packet = self.state.packet('initial', 'A')
        event = self.accept('initial', updates=[card()], packet=packet)
        path = self.root/'initial.json'; result = json.loads(path.read_text())
        history = self.state.history_packet('recorder')
        self.accept('future', owner='B', updates=[card()])
        self.assertEqual(self.state.accept('initial', 'A', result, path, packet), event)
        self.assertEqual(self.state.packet('initial', 'A'), packet)
        self.assertEqual(self.state.history_packet('recorder'), history)
        changed = copy.deepcopy(result); changed['hypothesis_updates'][0]['assumption'] = 'Changed'
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.state.validate('initial', 'A', changed, packet)
        self.assertEqual(len(self.state.events()), 2)

    def test_source_tampering_detected(self):
        self.accept('initial', updates=[card()])
        (self.root/'initial.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'source result changed'):
            self.state.current()

    def test_new_consequence_prevents_false_stagnation_even_after_learning(self):
        self.accept('initial', updates=[card()])
        self.accept('r1_return_0_learn_0', updates=[card(base=1, implications=['If true, two cases differ'])])
        pilot = InquiryPilot.__new__(InquiryPilot)
        pilot.run, pilot.hypotheses = self.root, self.state
        rows = [{'result': {'exploration': {'stalled_reason': 'No new observations',
                                           'understanding_changed': False}}}]
        progress = pilot.progress(1, rows, [], [])
        self.assertEqual(progress['disposition'], 'continue_with_next_actions')
        self.accept('r2_exchange_0', updates=[card(base=2, implications=['If true, two cases differ'],
                                                   reason='Only restating the same idea')])
        progress = pilot.progress(2, rows, [], [])
        self.assertEqual(progress['hypothesis_changes'], [])
        self.assertEqual(progress['disposition'], 'park_with_explicit_reasons')


if __name__ == '__main__':
    unittest.main()
