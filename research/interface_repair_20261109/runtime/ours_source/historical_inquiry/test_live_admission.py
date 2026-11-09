"""Regressions for reference notation actually emitted by the first live v2 actor."""
import copy
import tempfile
from pathlib import Path
import unittest

from fish_inquiry import admit_reference_layout, RecordLedger
from fish_materials import CASE
from inquiry_services import InquiryBroker
from test_review_fixes import CONFIG


class LiveReferenceAdmission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.broker = InquiryBroker(CASE, self.root/'services', CONFIG, fetch=lambda _: '{}')

    def answer(self):
        claim = {'id': 'C1', 'text': 'An observed coordinate change', 'kind': 'observation',
                 'use': 'exploratory', 'consequence': '',
                 'basis': {'source_ids': ['measurements.json'], 'record_ids': ['R07']}, 'depends_on': []}
        later = copy.deepcopy(claim); later.update(id='C2', depends_on=['C1'])
        return {'summary': 'Original science', 'evidence_claims': [claim, later], 'doubts': [],
                'initial_question': 'Original question', 'learning_request': {'needed': True, 'queries': ['Original query']}}

    def test_measured_basis_retained_and_local_dependency_resolves(self):
        raw = self.answer(); untouched = copy.deepcopy(raw)
        result = admit_reference_layout(raw, 'initial', self.broker)
        self.assertEqual(raw, untouched)
        self.assertEqual(result['evidence_claims'][0]['basis'],
                         {'source_ids': [], 'record_ids': ['R07'], 'measurement_sources': ['measurements.json']})
        self.assertEqual(result['evidence_claims'][1]['depends_on'], ['initial:C1'])
        for key in ('summary', 'initial_question', 'learning_request'):
            self.assertEqual(result[key], raw[key])
        ledger = RecordLedger(self.root/'ledger')
        ledger.validate('initial', 'A', result)
        for c in result['evidence_claims']:
            self.broker.check_basis(c['basis'])
        self.assertEqual(admit_reference_layout(result, 'initial', self.broker), result)

    def test_unknown_sources_and_future_dependencies_still_rejected(self):
        raw = self.answer(); raw['evidence_claims'][0]['basis']['source_ids'] = ['unseen_source']
        result = admit_reference_layout(raw, 'initial', self.broker)
        with self.assertRaisesRegex(ValueError, 'Unavailable source'):
            self.broker.check_basis(result['evidence_claims'][0]['basis'])
        raw = self.answer(); raw['evidence_claims'][0]['depends_on'] = ['C2']
        result = admit_reference_layout(raw, 'initial', self.broker)
        with self.assertRaisesRegex(ValueError, 'earlier exact'):
            RecordLedger(self.root/'ledger').validate('initial', 'A', result)


if __name__ == '__main__':
    unittest.main()
