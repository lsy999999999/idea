"""Trajectory arithmetic and end-to-end isolation tests; actor outputs are fixtures."""
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
from scipy.io import loadmat

from fish_materials import CASE, PROPOSAL, Broker, digest, verify
from fish_pilot import FishPilot, RecordLedger, RESEARCHERS
from prepare import save
from test_question_state import decision


def result():
    return {'summary': 'Fixture, not scientific evidence', 'artifacts': [], 'evidence': [],
            'claims': [], 'limitations': [], 'next_actions': [], 'evidence_claims': [], 'doubts': []}


def claim(cid, deps=None):
    return {'id': cid, 'text': 'A consequential measurement interpretation', 'kind': 'inference',
            'use': 'research_decision', 'consequence': 'Changes the selected analysis',
            'basis': {'source_ids': [], 'record_ids': ['R01']}, 'depends_on': deps or []}


class MaterialsTests(unittest.TestCase):
    def setUp(self):
        self.broker = Broker(CASE)

    def test_all_screened_values_exactly_match_archive_layout(self):
        verify(CASE)
        provenance = json.loads((CASE/'controller_only/provenance.json').read_text())
        with zipfile.ZipFile(PROPOSAL/'controller_only/materials.zip') as archive:
            for entry in provenance['mapping']:
                original = loadmat(io.BytesIO(archive.read(entry['archive_member'])), simplify_cells=True)
                p, q = self.broker.arrays(entry['record_id'])
                np.testing.assert_array_equal(p, original['trajectories'])
                np.testing.assert_array_equal(q, original['probtrajectories'])
        self.assertEqual(sum(r['frames'] for r in self.broker.records.values()), 584987)

    def test_source_and_path_escape_fail_closed(self):
        for request in ({'source_ids': ['https://doi.org/10.1098/rspb.2017.0224']},
                        {'source_ids': ['F5']}, {'source_ids': [{}]},
                        {'record_ids': ['../controller_only/provenance.json']},
                        {'url': 'https://example.org'}, {'operations': ['code']}):
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.broker.request(request)
        self.assertTrue(all(s['date'] < '2010-01-01' for s in self.broker.sources.values()))

    def synthetic(self, positions, score=None):
        scores = np.zeros(positions.shape[:2]) if score is None else score
        return patch.object(self.broker, 'arrays', return_value=(positions, scores))

    def test_native_units_derivative_and_valid_smoothing(self):
        t = np.arange(20.)
        p = np.zeros((20, 2, 2))
        p[:, 0, 0], p[:, 1, 0] = 2*t, 2*t+5
        with self.synthetic(p):
            out = self.broker.operation({'kind': 'motion', 'record_id': 'R01', 'derivative_lag': 3, 'smoothing': 4})
        self.assertEqual(out['used_position_frames'], 17)
        self.assertEqual(out['finite_velocity_pairs'], 14)
        self.assertEqual(out['speed_quantiles_by_object'], [[2., 2., 2.], [2., 2., 2.]])
        self.assertEqual(out['distance_quantiles'], [5., 5., 5.])

    def test_derivative_does_not_bridge_missing_or_filtered_interiors(self):
        p = np.zeros((5, 2, 2))
        p[:, :, 0] = np.arange(5)[:, None]
        q = np.zeros((5, 2)); q[2] = -1
        with self.synthetic(p, q):
            out = self.broker.operation({'kind': 'motion', 'record_id': 'R01', 'derivative_lag': 3, 'score_filter': 'nonnegative'})
        self.assertEqual(out['finite_velocity_pairs'], 0)
        self.assertEqual(out['mean_cosine_displacement_alignment'], None)

    def test_positive_lag_compares_A_earlier_with_B_later(self):
        rng = np.random.default_rng(123)
        a = rng.normal(size=(60, 2))
        b = np.vstack([rng.normal(size=(3, 2)), a[:-3]])
        v = np.stack([a, b], axis=1)
        p = np.concatenate([np.zeros((1, 2, 2)), np.cumsum(v, axis=0)])
        with self.synthetic(p):
            out = self.broker.operation({'kind': 'lag_correlation', 'record_id': 'R01', 'lags': [-3, 0, 3]})
        self.assertAlmostEqual(out['correlations'][2]['centered_vector_correlation'], 1.)
        self.assertLess(abs(out['correlations'][0]['centered_vector_correlation']), .4)

    def test_short_windows_and_unavailable_lags_are_explicit(self):
        with self.synthetic(np.zeros((5, 2, 2))):
            with self.assertRaisesRegex(ValueError, 'too short'):
                self.broker.operation({'kind': 'motion', 'record_id': 'R01', 'smoothing': 5})
            out = self.broker.operation({'kind': 'lag_correlation', 'record_id': 'R01', 'lags': [-60, 0, 60]})
        self.assertEqual(out['correlations'][0]['paired_rows'], 0)
        self.assertIsNone(out['correlations'][2]['centered_vector_correlation'])


class PipelineTests(unittest.TestCase):
    def test_record_dependencies_and_original_hash_survive_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); ledger = RecordLedger(root/'ledger')
            r = {**result(), 'evidence_claims': [claim('a'), claim('b', ['first:a'])]}
            path = root/'result.json'; save(path, r)
            ledger.observe('first', 'A', r, path)
            RecordLedger(root/'ledger').validate('first', 'A', copy.deepcopy(r))
            self.assertEqual(ledger.claims()['first:b']['basis']['record_ids'], ['R01'])
            changed = copy.deepcopy(r); changed['summary'] = 'changed'
            with self.assertRaisesRegex(ValueError, 'changed'):
                ledger.validate('first', 'A', changed)

    def test_two_round_pipeline_learning_corrections_freeze_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp)/'case'
            shutil.copytree(CASE/'allowed', case/'allowed')
            shutil.copytree(CASE/'controller_only', case/'controller_only')
            old = case/'legacy.json'; save(old, {'unchanged': True})
            save(case/'controller_only/protected_hashes.json', {str(old): digest(old)})
            seen = {}

            def fake(prompt, attempt, timeout):
                attempt = Path(attempt); attempt.mkdir(parents=True)
                (attempt/'prompt.txt').write_text(prompt)
                save(attempt/'execution_audit.json', {'returncode': 0, 'tool_events': 0, 'requested_model': 'gpt-6-luna'})
                context = json.loads(prompt.split('INPUTS:\n', 1)[1]); sid = context['_stage']
                seen[sid] = context
                r = result(); rid = context.get('researcher')
                if sid.startswith('01_initial_'):
                    self.assertEqual(context['evidence_state']['claims'], [])
                    r['initial_question'] = 'Independent inquiry '+rid
                elif rid:
                    r['personal_question_update'] = decision(context['question_state']['self'])
                    r['shared_question_update'] = None
                if sid == '01_initial_0':
                    r['evidence_claims'] = [claim('a')]
                if sid == 'r1_exchange_1':
                    r['evidence_claims'] = [claim('b', ['01_initial_0:a'])]
                if '_exchange_' in sid:
                    r['learning_request'] = {'needed': sid == 'r1_exchange_0', 'source_ids': ['F4'],
                        'operations': [{'kind': 'motion', 'record_id': 'R01', 'start': 1000, 'stop': 1200}]}
                if rid:
                    n = {'key': 'motion_question', 'title': 'Motion interpretation', 'kind': 'interpretation',
                         'mastery': 'read', 'understanding': 'Scoped inquiry', 'conditions': 'Sampled tracks only',
                         'example': 'Native units per frame', 'open_questions': 'Identity remains unknown',
                         'tags': ['motion', 'memory'], 'sources': ['measurements.json'], 'revision_reason': 'Continue inquiry'}
                    for item in context.get('memory', {}).get('retrieved', []):
                        if item['note']['key'] == n['key'] and item['note']['kind'] == 'correction':
                            n = {**item['note'], 'revision_reason': 'Preserve prior correction'}
                    r['memory_notes'] = [n]
                if 'verification_report' in context:
                    r['verification_responses'] = [{'claim_ref': f['claim_ref'], 'stance': 'accept',
                        'reason': 'Scoped report evidence', 'changed_understanding': 'Withdraw motivation only',
                        'question_effect': 'retain'} for f in context['verification_report']['findings']]
                    r['memory_notes'] = [{**n, 'kind': 'correction', 'revision_reason': 'Review finding',
                        'sources': list(set(n['sources']) | {context['verification_report_path']})}
                        for n in context['affected_notes'] or r['memory_notes']]
                if sid.endswith('_verify'):
                    r['findings'] = [{'claim_ref': c['ref'], 'status': 'undetermined',
                        'reason': 'Fixture evidence insufficient', 'evidence_refs': ['motion:R01'],
                        'corrected_claim': None} for c in context['targets']]
                if sid == '05_candidates':
                    r['ideas'] = [{'id': 'Q1', 'idea': 'An unfinished question', 'motivation': 'Corrected premise'}]
                if sid == '06_final_check':
                    self.assertTrue((case/'runs/test/GENERATION_FREEZE.json').exists())
                    self.assertIn('actual_broker_evidence', context)
                    r['checks'] = [{'idea_id': 'Q1', 'prior_work': {'verdict': 'unclear', 'reason': 'FINAL_ONLY'},
                        'math': {'verdict': 'no_obvious_error', 'reason': 'FINAL_ONLY'},
                        'novelty': {'coverage': 'unclear'}}]
                return r

            with patch('fish_pilot.invoke', side_effect=fake):
                pilot = FishPilot(case, 30, 'test'); pilot.execute()
            self.assertEqual(len([s for s in seen if '_discuss_' in s]), 3)
            self.assertIn('computed', seen['r1_learn_0']['broker_reply'])
            self.assertEqual(seen['r1_learn_0']['broker_reply']['sources'][0]['id'], 'F4')
            self.assertNotIn('rounds', seen['04_fresh_continuation'])
            self.assertTrue(seen['04_fresh_continuation']['memory']['retrieved'])
            self.assertEqual(len(pilot.questions.current()['personal']), 3)
            for rid, _ in RESEARCHERS:
                self.assertGreater(pilot.memory.index(rid)['notes']['motion_question']['version'], 1)
            self.assertEqual(json.loads((pilot.run/'AUDIT.json').read_text())['status'], 'pass')
            with patch('fish_pilot.invoke', side_effect=AssertionError('Resume must not call actors')):
                FishPilot(case, 30, 'test').execute()
            for context in seen.values():
                if context['_stage'] != '06_final_check':
                    self.assertNotIn('FINAL_ONLY', json.dumps(context))


if __name__ == '__main__':
    unittest.main()
