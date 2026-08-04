import tempfile
import unittest
from pathlib import Path

from scripts.init_index import connect, initialize


class IndexTests(unittest.TestCase):
    def test_initialize_creates_required_tables_and_foreign_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = connect(str(Path(directory) / "index.sqlite"))
            initialize(connection)
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertTrue(
                {"candidates", "publications", "authorships", "evidence", "coverage"}
                <= tables
            )
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
