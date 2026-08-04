import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_records import import_file
from scripts.init_index import connect, initialize


FIXTURE = Path(__file__).parent / "fixtures" / "records.jsonl"


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.connection = connect(str(Path(self.directory.name) / "index.sqlite"))
        initialize(self.connection)

    def tearDown(self):
        self.connection.close()
        self.directory.cleanup()

    def test_import_normalizes_and_preserves_stable_identities(self):
        summary = import_file(self.connection, str(FIXTURE))
        self.assertEqual(summary["candidates"], 4)
        self.assertEqual(summary["duplicate_publications"], 1)
        venue = self.connection.execute(
            "SELECT normalized_venue FROM publications WHERE source_id = 'p-neurips'"
        ).fetchone()[0]
        self.assertEqual(venue, "NeurIPS")
        co_first = self.connection.execute(
            "SELECT COUNT(*) FROM authorships WHERE category = 'co_first'"
        ).fetchone()[0]
        self.assertEqual(co_first, 1)
        same_name = self.connection.execute(
            "SELECT COUNT(*) FROM candidates WHERE name = 'Alice Example'"
        ).fetchone()[0]
        self.assertEqual(same_name, 2)

    def test_confirmed_graduation_requires_evidence_url(self):
        record = json.loads(FIXTURE.read_text().splitlines()[0])
        record["evidence"][0]["url"] = ""
        path = Path(self.directory.name) / "invalid.jsonl"
        path.write_text(json.dumps(record) + "\n")
        with self.assertRaisesRegex(ValueError, "confirmed graduation evidence"):
            import_file(self.connection, str(path))

    def test_unknown_authorship_category_is_rejected(self):
        record = json.loads(FIXTURE.read_text().splitlines()[0])
        record["publications"][0]["category"] = "senior_author"
        path = Path(self.directory.name) / "invalid-category.jsonl"
        path.write_text(json.dumps(record) + "\n")
        with self.assertRaisesRegex(ValueError, "authorship category"):
            import_file(self.connection, str(path))


if __name__ == "__main__":
    unittest.main()
