import json
from pathlib import Path
import shutil
import tempfile
import unittest

from prepare import HERE, save
from run import broker, verify_sources
from learning_memory import digest
from isolated_cli import parse_response


class MaterialBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.case = Path(self.temp.name) / "case"
        shutil.copytree(HERE / "cases/airfoil_001/allowed", self.case / "allowed")
        shutil.copytree(HERE / "cases/airfoil_001/controller_only", self.case / "controller_only")

    def rewrite_sources(self, mutate):
        path = self.case / "allowed/sources.json"
        sources = json.loads(path.read_text())
        mutate(sources)
        save(path, sources)
        # A changed source may have a valid content hash but still violate scientific policy.
        hashes = json.loads((self.case / "controller_only/allowed_hashes.json").read_text())
        hashes["sources.json"] = digest(path)
        save(self.case / "controller_only/allowed_hashes.json", hashes)

    def test_material_mutation_rejected(self):
        path = self.case / "allowed/data.csv"
        path.write_text(path.read_text() + "0,0,0,0,0,0\n")
        with self.assertRaisesRegex(ValueError, "mutated"):
            verify_sources(self.case)

    def test_post_cutoff_rejected_even_with_matching_hash(self):
        self.rewrite_sources(lambda s: s[0].update(date="1988-01-01"))
        with self.assertRaisesRegex(ValueError, "Post-cutoff"):
            verify_sources(self.case)

    def test_source_report_rejected_even_if_date_is_older(self):
        restriction = json.loads((self.case / "controller_only/restriction.json").read_text())
        self.rewrite_sources(lambda s: s[0].update(url=restriction["source_paper"]["id"]))
        with self.assertRaisesRegex(ValueError, "Forbidden"):
            verify_sources(self.case)

    def test_request_cannot_escape_catalog(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            broker(self.case, {"source_ids": ["https://ntrs.nasa.gov/citations/19890016302"]})

    def test_broker_returns_actual_recorded_spectrum(self):
        reply = broker(self.case, {"source_ids": ["F3"], "spectrum_ids": [0]})
        self.assertEqual(reply["sources"][0]["date"], "1955-09-20")
        self.assertIn([800.0, 126.201], reply["spectra"][0]["frequency_and_level"])
        self.assertIsNone(reply["all_rows_csv"])

    def test_syntax_admission_preserves_scientific_string(self):
        raw = '{"question":"is f[c/U] relevant?", "memory_use":["note"}}'
        result = parse_response(raw)
        self.assertEqual(result["question"], "is f[c/U] relevant?")
        self.assertEqual(result["memory_use"], ["note"])
        self.assertEqual(result["controller_syntax_repairs"][0]["after"], "]")

    def test_syntax_admission_cannot_invent_missing_content(self):
        with self.assertRaises(json.JSONDecodeError):
            parse_response('{"question": "unfinished}')


if __name__ == "__main__":
    unittest.main()
