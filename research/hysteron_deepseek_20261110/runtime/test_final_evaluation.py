import json
from pathlib import Path
import tempfile
import unittest

from evaluate_frozen import FinalAdapter
from research_context import ContextStore


class FinalSources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = ContextStore(self.root / 'documents')
        self.path = self.root / 'accepted' / 'Kone.json'
        self.path.parent.mkdir()
        self.record = {'id': 'Kone', 'title': 'Actual work', 'url': 'https://example.org/one',
                       'date': '2020-01-01', 'date_evidence': {'verified': True}}
        self.path.write_text(json.dumps(self.record))
        self.store.add_file(self.path)
        self.adapter = object.__new__(FinalAdapter)
        self.adapter.ideas = []

    def candidate(self, **updates):
        source = {'source_id': 'Kone', 'title': 'Actual work', 'url': 'https://example.org/one',
                  'snapshot_path': '/obsolete/directory/Kone.json'}
        source.update(updates)
        return {'checks': [{'idea_id': 'I1', 'prior_work': {'sources': [source]}}]}

    def test_unique_registered_filename_restores_exact_snapshot(self):
        out = self.adapter.normalize(self.candidate(), {}, self.store)
        source = out['checks'][0]['prior_work']['sources'][0]
        self.assertEqual(source['snapshot_path'], str(self.path.resolve()))
        self.assertEqual(source['publication_date']['quote'], '2020-01-01')

    def test_source_identity_mixup_is_actionable(self):
        with self.assertRaisesRegex(ValueError, 'Source identity mismatch.*Actual work'):
            self.adapter.normalize(self.candidate(title='Another work'), {}, self.store)

    def test_wrong_date_reports_the_specific_registered_source(self):
        with self.assertRaisesRegex(ValueError, 'Publication provenance mismatch for Kone'):
            self.adapter.normalize(self.candidate(publication_date={'quote': '1990-01-01'}), {}, self.store)

    def test_ambiguous_basename_does_not_select_an_arbitrary_source(self):
        another = self.root / 'another' / 'Kone.json'
        another.parent.mkdir()
        another.write_text('{"id":"Kother"}')
        self.store.add_file(another)
        with self.assertRaisesRegex(ValueError, 'Unresolved or ambiguous snapshot_path'):
            self.adapter.normalize(self.candidate(), {}, self.store)


if __name__ == '__main__':
    unittest.main()
