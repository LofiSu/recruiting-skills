import tempfile
import unittest
from pathlib import Path

from scripts.import_records import import_file
from scripts.init_index import connect, initialize
from scripts.query_candidates import Query, query_candidates


FIXTURE = Path(__file__).parent / "fixtures" / "records.jsonl"
ALL_VENUES = (
    "ACL", "ICML", "ICLR", "NeurIPS", "EMNLP", "CVPR", "AAAI", "ICCV",
    "MLSys", "OSDI", "EuroSys", "ASPLOS", "ISCA", "SC", "PPoPP",
)
ALL_CATEGORIES = ("main_first", "co_first", "findings", "workshop", "short", "demo")


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.connection = connect(str(Path(self.directory.name) / "index.sqlite"))
        initialize(self.connection)
        import_file(self.connection, str(FIXTURE))

    def tearDown(self):
        self.connection.close()
        self.directory.cleanup()

    def test_query_separates_confirmed_and_inferred_and_excludes_ambiguous_identity(self):
        query = Query(
            graduation_years=(2027, 2028),
            degree_thresholds={"phd": 5, "masters": 3},
            venues=ALL_VENUES,
            categories=ALL_CATEGORIES,
            graduation_states=("confirmed", "likely_needs_verification"),
            strictly_greater=True,
        )
        result = query_candidates(self.connection, query)
        self.assertEqual(
            [row["candidate_id"] for row in result["confirmed"]],
            ["phd-2027", "ms-2028"],
        )
        self.assertEqual(
            [row["candidate_id"] for row in result["likely_needs_verification"]],
            ["phd-2028"],
        )
        self.assertTrue(all(row["qualifying_publications"] for row in result["confirmed"]))
        returned_ids = {
            row["candidate_id"]
            for section in ("confirmed", "likely_needs_verification")
            for row in result[section]
        }
        self.assertNotIn("ambiguous-2027", returned_ids)
        self.assertTrue(result["warnings"])

    def test_strictly_greater_and_category_policy_change_eligibility(self):
        strict = Query(
            graduation_years=(2027,),
            degree_thresholds={"phd": 6, "masters": 3},
            venues=ALL_VENUES,
            categories=ALL_CATEGORIES,
            graduation_states=("confirmed",),
            strictly_greater=True,
        )
        self.assertEqual(query_candidates(self.connection, strict)["confirmed"], [])

        main_only = Query(
            graduation_years=(2027,),
            degree_thresholds={"phd": 5, "masters": 3},
            venues=ALL_VENUES,
            categories=("main_first",),
            graduation_states=("confirmed",),
            strictly_greater=True,
        )
        self.assertEqual(query_candidates(self.connection, main_only)["confirmed"], [])

    def test_unsupported_venue_fails_fast(self):
        query = Query(
            graduation_years=(2027,),
            degree_thresholds={"phd": 0, "masters": 0},
            venues=("FakeConf",),
            categories=("main_first",),
            graduation_states=("confirmed",),
        )
        with self.assertRaisesRegex(ValueError, "unsupported venue"):
            query_candidates(self.connection, query)

    def test_stale_graduation_evidence_is_not_returned_as_confirmed(self):
        self.connection.execute(
            "UPDATE evidence SET retrieved_at = '2020-01-01' WHERE candidate_id = 'phd-2027'"
        )
        self.connection.commit()
        query = Query(
            graduation_years=(2027,),
            degree_thresholds={"phd": 5, "masters": 3},
            venues=ALL_VENUES,
            categories=ALL_CATEGORIES,
            graduation_states=("confirmed", "likely_needs_verification"),
            strictly_greater=True,
            max_evidence_age_days=365,
        )
        result = query_candidates(self.connection, query)
        self.assertEqual(result["confirmed"], [])
        self.assertEqual(result["likely_needs_verification"][0]["candidate_id"], "phd-2027")
        self.assertEqual(result["likely_needs_verification"][0]["graduation_state"], "stale")


if __name__ == "__main__":
    unittest.main()
