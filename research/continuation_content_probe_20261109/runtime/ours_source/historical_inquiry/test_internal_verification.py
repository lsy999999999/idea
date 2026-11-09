"""Meaningful correction routing regressions. Model responses are fixtures, not findings."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from internal_verification import EvidenceLedger, evidence_packet
from prepare import HERE, save
from question_state import file_hash
from run import Pilot, RESEARCHERS, broker
from test_question_state import decision


def claim(cid='coordinate', kind='inference', use='research_decision', depends_on=None):
    return {'id': cid, 'text': 'Raw peak separation refutes alignment in fc/U.',
            'kind': kind, 'use': use, 'consequence': 'Abandon that scale',
            'basis': {'source_ids': ['F1'], 'spectrum_ids': [50, 88]},
            'depends_on': depends_on or []}


def result():
    return {'summary': 'Fixture only', 'artifacts': [], 'evidence': [], 'claims': [],
            'limitations': [], 'next_actions': [], 'evidence_claims': [], 'doubts': []}


def setup_case(root):
    case = root / 'case'
    for subdir in ('allowed', 'controller_only'):
        shutil.copytree(HERE / 'cases/airfoil_001' / subdir, case / subdir)
    old = case / 'run/frozen.json'
    save(old, {'legacy': True})
    save(case / 'controller_only/protected_hashes.json', {str(old): file_hash(old)})
    return case


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ledger = EvidenceLedger(self.root / 'ledger')

    def observe(self, stage, claims, doubts=None):
        r = {**result(), 'evidence_claims': claims, 'doubts': doubts or []}
        path = self.root / (stage + '.json')
        save(path, r)
        self.ledger.observe(stage, 'A', r, path)
        return path

    def test_unproved_tentative_idea_is_deferred_without_verifier(self):
        self.observe('initial', [claim(kind='hypothesis', use='exploratory')],
                     [{'claim_ref': 'coordinate', 'type': 'unproved_hypothesis',
                       'reason': 'Not experimentally established', 'consequence': 'No evidence yet'}])
        batch = self.ledger.select('pause')
        self.assertEqual(batch['targets'], [])
        self.assertEqual(batch['deferred'][0]['disposition'], 'not_an_error_or_gate')

    def test_accepted_consequential_premise_checked_without_any_doubt(self):
        self.observe('initial', [claim()])
        self.assertEqual(self.ledger.select('pause')['targets'][0]['ref'], 'initial:coordinate')

    def test_transitive_dependents_marked_for_review_not_automatically_refuted(self):
        self.observe('initial', [claim()])
        self.observe('peer', [claim('dependent', depends_on=['initial:coordinate'])])
        affected = self.ledger.relevant(['initial:coordinate'])
        self.assertEqual({c['ref'] for c in affected}, {'initial:coordinate', 'peer:dependent'})
        self.assertTrue(all('verdict' not in c for c in affected))

    def test_budget_limits_calls_and_keeps_unchecked_claims(self):
        self.ledger = EvidenceLedger(self.root / 'bounded', max_checks=1, batch_size=1)
        self.observe('initial', [claim('a'), claim('b')])
        batch = self.ledger.select('first')
        report = self.root / 'report.json'
        save(report, {'findings': [{'claim_ref': 'initial:a', 'status': 'undetermined'}]})
        self.ledger.record_report('first', json.loads(report.read_text()), report)
        following = self.ledger.select('second')
        self.assertEqual(batch['pending_refs'], ['initial:b'])
        self.assertTrue(following['budget_exhausted'])
        self.assertEqual(following['pending_refs'], ['initial:b'])

    def test_forged_refs_and_mutated_sources_rejected(self):
        with self.assertRaisesRegex(ValueError, 'earlier exact'):
            self.observe('bad', [claim(depends_on=['nonexistent:id'])])
        path = self.observe('valid', [claim()])
        path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'provenance'):
            self.ledger.claims()

    def test_recomputes_both_coordinates_and_preserves_conditions(self):
        self.observe('initial', [claim()])
        case = setup_case(self.root)
        packet = evidence_packet(case, list(self.ledger.claims().values()), self.ledger.claims(), broker)
        catalog = packet['evidence_catalog']
        self.assertAlmostEqual(catalog['arithmetic:50']['peak_f_chord_over_U'][0], 4.040909090909091)
        self.assertAlmostEqual(catalog['arithmetic:88']['peak_f_chord_over_U'][0], 4.105050505050505)
        self.assertEqual(catalog['arithmetic:50']['sampled_peak_hz'], [3150.0])
        self.assertNotEqual(catalog['spectrum:50']['conditions']['suction-side-displacement-thickness'],
                            catalog['spectrum:88']['conditions']['suction-side-displacement-thickness'])

    def test_verifier_cannot_cite_unseen_evidence_or_skip_target(self):
        target = {'ref': 'initial:x'}
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.ledger.validate_findings({'findings': []}, [target], {})
        with self.assertRaisesRegex(ValueError, 'outside'):
            self.ledger.validate_findings({'findings': [{'claim_ref': target['ref'], 'status': 'supported',
                                         'reason': 'text', 'evidence_refs': ['new_paper']}]}, [target], {})

    def test_structured_claims_alias_and_local_dependencies_preserve_content(self):
        r = {**result(), 'claims': [claim('first'), claim('second', depends_on=['local:first'])]}
        del r['evidence_claims']
        del r['doubts']
        admitted = Pilot.admit_bookkeeping(copy.deepcopy(r), researcher=True)
        self.assertEqual(admitted['claims'], r['claims'])
        self.assertEqual(admitted['evidence_claims'], r['claims'])
        self.ledger.validate('local', 'A', admitted)
        self.assertFalse(admitted['controller_admission']['scientific_content_changed'])

    def test_explicit_data_source_fetches_actual_rows_without_opening_literature(self):
        c = claim()
        c['basis'] = {'source_ids': ['data.csv'], 'spectrum_ids': []}
        self.observe('initial', [c])
        case = setup_case(self.root)
        packet = evidence_packet(case, list(self.ledger.claims().values()), self.ledger.claims(), broker)
        self.assertIn('csv', packet['evidence_catalog']['data.csv'])
        self.assertGreater(len(packet['evidence_catalog']['data.csv']['csv']), 1000)

    def test_verifier_alias_resolves_only_unique_supplied_ids(self):
        r = {**result(), 'claims': [{'id': 'x', 'status': 'undetermined', 'reason': 'Missing material',
                                     'evidence_refs': [], 'corrected_claim': None}]}
        admitted = Pilot.admit_bookkeeping(copy.deepcopy(r), verifier_targets=[{'id': 'x', 'ref': 'initial:x'}])
        self.assertEqual(admitted['findings'][0]['claim_ref'], 'initial:x')
        self.assertEqual(admitted['claims'], r['claims'])
        self.ledger.validate_findings(admitted, [{'ref': 'initial:x'}], {})


class CorrectionPipelineTests(unittest.TestCase):
    def test_later_run_can_reuse_internal_correction_but_cannot_drop_its_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = setup_case(Path(tmp))
            first = Pilot(case, 30, 'first_v3')
            path = first.run / 'stages/internal_verify/result.json'
            save(path, {'findings': [{'claim_ref': 'old:x', 'status': 'undetermined'}]})
            first.evidence.record_report('old', json.loads(path.read_text()), path)
            r = {**result(), 'memory_notes': [{'key': 'prior_correction', 'title': 'Prior scoped correction',
                'kind': 'correction', 'mastery': 'read', 'understanding': 'A previously unresolved discrepancy',
                'conditions': 'Same immutable case', 'example': 'A traceable report', 'open_questions': 'Still unresolved',
                'tags': ['flow'], 'sources': ['data.csv', str(path.resolve())]}]}
            note_path = first.run / 'old_note.json'
            save(note_path, r)
            rid = RESEARCHERS[0][0]
            first.memory.commit(rid, first.task_id, 'prior', note_path)
            later = Pilot(case, 30, 'later_v3')
            r['memory_notes'][0]['revision_reason'] = 'Continued learning; preserve prior report'
            later.validate(r, True, rid)
            r['memory_notes'][0]['sources'] = ['data.csv']
            with self.assertRaisesRegex(ValueError, 'retain provenance'):
                later.validate(r, True, rid)

    def test_unadmitted_answer_with_different_prompt_is_not_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = setup_case(Path(tmp))
            pilot = Pilot(case, 30)
            attempt = pilot.run / 'stages/08_recorder/attempt-001'
            attempt.mkdir(parents=True)
            (attempt / 'prompt.txt').write_text('A different scientific input')
            save(attempt / 'execution_audit.json', {'returncode': 0, 'tool_events': 0})
            save(attempt / 'final.txt', {**result(), 'summary': 'Do not reuse this claim'})
            with patch('run.invoke', return_value={**result(), 'summary': 'Fresh correct input'}) as invoke:
                output = pilot.call('08_recorder', 'recorder', 'Current task', {})
            self.assertEqual(output['summary'], 'Fresh correct input')
            self.assertEqual(invoke.call_count, 1)

    def test_actual_controller_reengages_both_peers_versions_notes_and_isolates_judge(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = setup_case(Path(tmp))
            seen = {}
            memory_at_judge = {}

            def fake(prompt, attempt, timeout):
                sid = Path(attempt).parent.name
                context = json.loads(prompt.split('INPUTS:\n', 1)[1])
                seen[sid] = context
                r = result()
                rid = context.get('researcher')
                if sid.startswith('01_initial_'):
                    r['initial_question'] = 'Can spectra be made comparable? ' + rid
                elif rid:
                    r['personal_question_update'] = decision(context['question_state']['self'])
                    r['shared_question_update'] = None
                if sid == '01_initial_0':
                    r['evidence_claims'] = [claim()]
                if sid == '02_exchange_1':
                    r['evidence_claims'] = [claim('accepted', depends_on=['01_initial_0:coordinate'])]
                if sid == '04_return_1':
                    r['evidence_claims'] = [claim('later', kind='hypothesis', use='exploratory',
                                                 depends_on=['01_initial_0:coordinate'])]
                if sid.startswith('02_exchange_'):
                    r['learning_request'] = {'needed': False}
                if rid and not sid.startswith('02_exchange_'):
                    r['memory_notes'] = [{'key': 'scale_note', 'title': 'Scale interpretation',
                        'kind': 'interpretation', 'mastery': 'read', 'understanding': 'A scoped tentative idea',
                        'conditions': 'Sampled data only', 'example': 'Compare peaks', 'open_questions': 'Full shape?',
                        'tags': ['flow', 'spectrum'], 'sources': ['data.csv'], 'revision_reason': 'Updated evidence'}]
                    for item in context.get('memory', {}).get('retrieved', []):
                        n = item['note']
                        if n['key'] == 'scale_note' and n['kind'] == 'correction':
                            r['memory_notes'] = [{**n, 'revision_reason': 'Retain scoped correction while continuing'}]
                if 'verification_report' in context:
                    # Peer zero accepts; peer one retains a reasoned unresolved position.
                    r['verification_responses'] = [{'claim_ref': f['claim_ref'],
                        'stance': 'accept' if sid.endswith('_0') else 'unresolved',
                        'reason': 'Coordinates must be distinguished; global shape unresolved',
                        'changed_understanding': 'Remove this counterexample only', 'question_effect': 'retain'}
                        for f in context['verification_report']['findings']]
                    r['memory_notes'] = [{**n, 'kind': 'correction', 'revision_reason': 'Report reviewed',
                        'understanding': 'Counterexample withdrawn or disputed; full shape still an open question',
                        'sources': ['data.csv', context['verification_report_path']]}
                        for n in context['affected_notes']] or [{**n, 'kind': 'correction',
                            'sources': ['data.csv', context['verification_report_path']]}
                            for n in r['memory_notes']]
                if sid.endswith('_verify'):
                    r['findings'] = [{'claim_ref': t['ref'], 'status': 'needs_correction',
                        'reason': '3150*.0508/39.6=4.0409 and 1600*.1016/39.6=4.1051',
                        'evidence_refs': ['arithmetic:50', 'arithmetic:88'],
                        'corrected_claim': 'Raw frequencies differ but these normalized sampled peaks nearly align'}
                        for t in context['targets']]
                if sid == '05_candidates':
                    r['ideas'] = [{'id': 'q', 'idea': 'Can full spectra be compared under a common scale?',
                                   'motivation': 'Question retained after withdrawing faulty evidence'}]
                if sid == '06_check':
                    self.assertTrue((case / 'runs/inquiry_v3/GENERATION_FREEZE.json').exists())
                    memory_at_judge.update({str(p): file_hash(p) for p in (case / 'researchers').rglob('*.json')})
                    r['checks'] = [{'idea_id': 'q', 'prior_work': {'status': 'unclear', 'reason': 'FINAL_JUDGE_ONLY', 'sources': []},
                                    'math': {'status': 'no_obvious_error', 'reason': 'FINAL_JUDGE_ONLY'}}]
                return r

            with patch('run.invoke', side_effect=fake):
                pilot = Pilot(case, 30)
                pilot.execute()
            self.assertIn('02b_exchange_discuss_0', seen)
            self.assertIn('02b_exchange_discuss_1', seen)
            self.assertTrue(seen['02b_exchange_discuss_1']['earlier_peer_responses'])
            self.assertEqual(seen['01_initial_1']['evidence_state']['claims'], [])
            # Post-correction continuation receives current notes, not obsolete interpretation.
            notes = seen['07_fresh_continuation']['memory']['retrieved']
            self.assertTrue(any(n['note']['kind'] == 'correction' for n in notes))
            for path, expected in memory_at_judge.items():
                self.assertEqual(file_hash(path), expected)
            self.assertFalse(any('FINAL_JUDGE_ONLY' in p.read_text() for p in (case / 'researchers').rglob('*.json')))
            # Raw note v1 and all intervening versions remain readable.
            versions = list((case / 'researchers' / RESEARCHERS[0][0] / 'notes/scale_note').glob('v*.json'))
            self.assertGreater(len(versions), 1)
            self.assertEqual(json.loads(sorted(versions)[0].read_text())['kind'], 'interpretation')
            before = pilot.questions.current()
            with patch('run.invoke', side_effect=AssertionError('Resume must not call model')):
                Pilot(case, 30).execute()
            self.assertEqual(pilot.questions.current(), before)


if __name__ == '__main__':
    unittest.main()
