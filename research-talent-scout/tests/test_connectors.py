import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from scripts.connectors.http import ConnectorError, JsonClient, Response
from scripts.connectors.mapping import AuthorDraft, PublicationDraft, canonical_venue, to_records
from scripts.connectors.openalex import fetch_openalex, works_to_drafts
from scripts.connectors.semanticscholar import fetch_semanticscholar
from scripts.fetch_records import build_parser, run
from scripts.import_records import import_file
from scripts.init_index import connect, initialize
from scripts.query_candidates import Query, query_candidates


FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample-records.jsonl"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ScriptedTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, url, headers):
        self.calls.append((url, headers))
        if not self.responses:
            raise AssertionError(f"unexpected request {url}")
        status, body, response_headers = self.responses.pop(0)
        if isinstance(body, dict):
            payload = json.dumps(body).encode("utf-8")
        else:
            payload = body
        return Response(status, payload, response_headers)


def _client(transport) -> JsonClient:
    return JsonClient(transport, delay=0, max_retries=3, sleeper=lambda _seconds: None)


def _query(connection):
    return query_candidates(
        connection,
        Query(
            graduation_years=(2027,),
            degree_thresholds={"phd": 0, "masters": 0},
            venues=("NeurIPS",),
            categories=("main_first",),
            graduation_states=("unknown",),
            strictly_greater=True,
            max_evidence_age_days=None,
        ),
    )


class MappingTests(unittest.TestCase):
    def test_venue_alias_matches_proceedings_titles_and_not_short_substrings(self):
        self.assertEqual(canonical_venue("NeurIPS"), "NeurIPS")
        self.assertEqual(
            canonical_venue("Advances in Neural Information Processing Systems 37"),
            "NeurIPS",
        )
        self.assertEqual(canonical_venue("SC"), "SC")
        self.assertIsNone(canonical_venue("Science"))
        self.assertIsNone(canonical_venue("NeurIPS Workshops"))

    def test_workshop_string_does_not_become_main_first(self):
        drafts, _warnings = works_to_drafts(
            [
                {
                    "id": "https://openalex.org/W1000000003",
                    "title": "Fixture Workshop Paper",
                    "publication_year": 2025,
                    "primary_location": {
                        "source": {
                            "display_name": "Neural Information Processing Systems Workshops"
                        },
                        "landing_page_url": "https://example.org/workshop",
                    },
                    "authorships": [
                        {
                            "author_position": "first",
                            "author": {
                                "id": "https://openalex.org/A5000000001",
                                "display_name": "Ada Fixture",
                            },
                            "institutions": [],
                            "raw_affiliation_strings": ["Example University"],
                        }
                    ],
                }
            ]
        )
        publication = drafts[0].publications[0]
        self.assertEqual(publication.venue, "NeurIPS")
        self.assertEqual(publication.category, "workshop")

    def test_email_shaped_affiliation_text_is_removed(self):
        records = to_records(
            [
                AuthorDraft(
                    source="openalex",
                    author_id="A5000000001",
                    name="Ada Fixture",
                    profile_url="https://openalex.org/A5000000001",
                    institution="Example University ada@example.edu",
                    institution_url="https://example.org/fixture-neurips",
                    institution_excerpt="Affiliation ada@example.edu",
                    publications=[
                        PublicationDraft(
                            source_id="openalex:W1000000001",
                            title="Fixture NeurIPS Paper",
                            year=2024,
                            venue="NeurIPS",
                            category="main_first",
                            url="https://example.org/fixture-neurips",
                        )
                    ],
                )
            ],
            degree="phd",
            retrieved_at="2026-10-29",
        )
        encoded = json.dumps(records)
        self.assertEqual(records[0]["candidate"]["institution"], "Example University")
        self.assertNotIn("@", encoded)
        self.assertEqual(records[0]["candidate"]["graduation_state"], "unknown")
        self.assertNotIn("mailto:", encoded)


class OpenAlexConnectorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.connection = connect(str(Path(self.directory.name) / "index.sqlite"))
        initialize(self.connection)

    def tearDown(self):
        self.connection.close()
        self.directory.cleanup()

    def test_venue_fetch_imports_and_query_keeps_graduation_unconfirmed(self):
        transport = ScriptedTransport(
            [
                (200, _load("openalex_sources.json"), {}),
                (200, _load("openalex_works.json"), {}),
            ]
        )
        records, warnings = fetch_openalex(
            _client(transport),
            degree="phd",
            retrieved_at="2026-10-29",
            api_key_present=False,
            venue="NeurIPS",
            year=2024,
            graduation_year=2027,
        )
        self.assertEqual([record["candidate"]["id"] for record in records], ["openalex:A5000000001", "openalex:A5000000002"])
        ada = records[0]
        self.assertEqual(ada["candidate"]["graduation_state"], "unknown")
        self.assertEqual(ada["candidate"]["degree"], "phd")
        self.assertEqual(ada["candidate"]["institution"], "Example University AI Lab")
        self.assertEqual(ada["publications"][0]["category"], "main_first")
        self.assertEqual(ada["publications"][0]["venue"], "NeurIPS")
        self.assertEqual(ada["publications"][0]["url"], "https://example.org/fixture-neurips")
        self.assertEqual(records[1]["publications"][0]["category"], "unclassified")
        self.assertTrue(all(item["state"] == "unknown" for item in ada["evidence"] if item["field"] == "graduation_year"))
        self.assertNotIn("@", json.dumps(records))
        self.assertTrue(any("not a confirmed" in warning or "not confirmed" in warning for warning in warnings))
        self.assertTrue(any("first page" in warning for warning in warnings))

        works_url = transport.calls[1][0]
        params = parse_qs(urlparse(works_url).query)
        self.assertIn("S9990000001", params["filter"][0])
        self.assertIn("publication_year:2024", params["filter"][0])
        self.assertEqual(params["page"], ["1"])
        self.assertNotIn("cursor", params)
        self.assertNotIn("api_key", works_url)

        path = Path(self.directory.name) / "records.jsonl"
        path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
        summary = import_file(self.connection, str(path))
        self.assertEqual(summary["candidates"], 2)
        self.assertEqual(summary["publications"], 1)
        self.assertEqual(summary["duplicate_publications"], 1)
        result = _query(self.connection)
        self.assertEqual(result["confirmed"], [])
        self.assertEqual(
            [row["candidate_id"] for row in result["likely_needs_verification"]],
            ["openalex:A5000000001"],
        )
        self.assertEqual(result["likely_needs_verification"][0]["qualifying_count"], 1)
        self.assertEqual(result["likely_needs_verification"][0]["graduation_state"], "unknown")

    def test_cursor_is_followed_only_when_an_api_key_is_present(self):
        first_page = _load("openalex_works.json")
        first_page["results"] = first_page["results"][:1]
        transport = ScriptedTransport(
            [
                (200, _load("openalex_sources.json"), {}),
                (200, first_page, {}),
                (200, {"meta": {"next_cursor": None}, "results": []}, {}),
            ]
        )
        fetch_openalex(
            _client(transport),
            degree="phd",
            retrieved_at="2026-10-29",
            api_key_present=True,
            venue="NeurIPS",
            year=2024,
            max_works=25,
        )
        self.assertEqual(len(transport.calls), 3)
        self.assertEqual(parse_qs(urlparse(transport.calls[2][0]).query)["cursor"], ["cursor-2"])

    def test_unknown_venue_does_not_call_http(self):
        transport = ScriptedTransport([])
        with self.assertRaisesRegex(ValueError, "unsupported venue"):
            fetch_openalex(
                _client(transport),
                degree="phd",
                retrieved_at="2026-10-29",
                api_key_present=False,
                venue="Nature",
                year=2024,
            )
        self.assertEqual(transport.calls, [])


class SemanticScholarConnectorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.connection = connect(str(Path(self.directory.name) / "index.sqlite"))
        initialize(self.connection)

    def tearDown(self):
        self.connection.close()
        self.directory.cleanup()

    def test_venue_search_imports_and_query_skips_unclassified_authors(self):
        transport = ScriptedTransport([(200, _load("s2_paper_search.json"), {})])
        records, warnings = fetch_semanticscholar(
            _client(transport),
            degree="masters",
            retrieved_at="2026-10-29",
            api_key_present=False,
            venue="NeurIPS",
            year=2024,
            graduation_year=2027,
        )
        params = parse_qs(urlparse(transport.calls[0][0]).query)
        self.assertEqual(params["venue"][0].split(",")[0], "NeurIPS")
        self.assertEqual(params["year"], ["2024"])
        self.assertNotIn("x-api-key", transport.calls[0][1])
        cara = next(record for record in records if record["candidate"]["id"] == "s2:1111111")
        drew = next(record for record in records if record["candidate"]["id"] == "s2:2222222")
        self.assertEqual(cara["publications"][0]["category"], "main_first")
        self.assertEqual(cara["publications"][0]["url"], "https://example.org/s2-fixture.pdf")
        self.assertEqual(drew["publications"][0]["category"], "unclassified")
        self.assertEqual(cara["candidate"]["homepage"], "")
        self.assertNotIn("@", json.dumps(records))
        self.assertTrue(any("not a complete venue census" in warning for warning in warnings))

        path = Path(self.directory.name) / "records.jsonl"
        path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
        import_file(self.connection, str(path))
        result = query_candidates(
            self.connection,
            Query(
                graduation_years=(2027,),
                degree_thresholds={"phd": 0, "masters": 0},
                venues=("NeurIPS",),
                categories=("main_first",),
                graduation_states=("unknown",),
                strictly_greater=True,
                max_evidence_age_days=None,
            ),
        )
        self.assertEqual(result["confirmed"], [])
        self.assertEqual(
            [row["candidate_id"] for row in result["likely_needs_verification"]],
            ["s2:1111111"],
        )

    def test_author_search_keeps_personal_homepage_and_workshop_category(self):
        transport = ScriptedTransport(
            [
                (200, _load("s2_author_search.json"), {}),
                (200, _load("s2_author_papers.json"), {}),
            ]
        )
        records, _warnings = fetch_semanticscholar(
            _client(transport),
            degree="phd",
            retrieved_at="2026-10-29",
            api_key_present=True,
            author="Cara Fixture",
        )
        self.assertEqual(len(records), 1)
        candidate = records[0]["candidate"]
        self.assertEqual(candidate["id"], "s2:1111111")
        self.assertEqual(candidate["homepage"], "https://example.edu/cara")
        self.assertNotIn("semanticscholar.org", candidate["homepage"])
        categories = {item["source_id"]: item["category"] for item in records[0]["publications"]}
        self.assertEqual(categories["s2:aaa111"], "main_first")
        self.assertEqual(categories["s2:ccc333"], "workshop")
        self.assertNotIn("@", json.dumps(records))
        self.assertIn("/author/search", transport.calls[0][0])
        self.assertIn("/author/1111111/papers", transport.calls[1][0])


class HttpClientTests(unittest.TestCase):
    def test_retries_429_then_reads_json(self):
        transport = ScriptedTransport(
            [
                (429, b"slow down", {"Retry-After": "0"}),
                (200, {"ok": True}, {}),
            ]
        )
        sleeps = []
        client = JsonClient(transport, delay=0, max_retries=3, sleeper=sleeps.append)
        self.assertEqual(client.get_json("https://api.semanticscholar.org/graph/v1/paper/search"), {"ok": True})
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(sleeps, [0.0])

    def test_error_body_redacts_secrets(self):
        transport = ScriptedTransport([(500, b"bearer super-secret-key leaked", {})])
        client = JsonClient(
            transport,
            delay=0,
            max_retries=0,
            secrets=("super-secret-key",),
            default_headers={"Authorization": "Bearer super-secret-key"},
        )
        with self.assertRaises(ConnectorError) as caught:
            client.get_json("https://api.openalex.org/works?api_key=super-secret-key")
        message = str(caught.exception)
        self.assertNotIn("super-secret-key", message)
        self.assertIn("REDACTED", message)
        self.assertEqual(transport.calls[0][1]["Authorization"], "Bearer super-secret-key")


class FetchRecordsCliTests(unittest.TestCase):
    def test_cli_writes_jsonl_that_imports(self):
        transport = ScriptedTransport(
            [
                (200, _load("openalex_sources.json"), {}),
                (200, _load("openalex_works.json"), {}),
            ]
        )
        output = Path(tempfile.mkdtemp()) / "records.jsonl"
        args = build_parser().parse_args(
            [
                "--source",
                "openalex",
                "--venue",
                "NeurIPS",
                "--year",
                "2024",
                "--degree",
                "phd",
                "--retrieved-at",
                "2026-10-29",
                "--output",
                str(output),
            ]
        )
        summary = run(args, client=_client(transport), api_key_present=False)
        self.assertEqual(summary["records"], 2)
        self.assertTrue(output.is_file())
        directory = tempfile.TemporaryDirectory()
        connection = connect(str(Path(directory.name) / "index.sqlite"))
        initialize(connection)
        imported = import_file(connection, str(output))
        self.assertEqual(imported["candidates"], 2)
        connection.close()
        directory.cleanup()

    def test_committed_sample_matches_the_openalex_fixture(self):
        transport = ScriptedTransport(
            [
                (200, _load("openalex_sources.json"), {}),
                (200, _load("openalex_works.json"), {}),
            ]
        )
        output = Path(tempfile.mkdtemp()) / "records.jsonl"
        args = build_parser().parse_args(
            [
                "--source",
                "openalex",
                "--venue",
                "NeurIPS",
                "--year",
                "2024",
                "--degree",
                "phd",
                "--retrieved-at",
                "2026-10-29",
                "--output",
                str(output),
            ]
        )
        run(args, client=_client(transport), api_key_present=False)
        self.assertEqual(output.read_text(encoding="utf-8"), SAMPLE.read_text(encoding="utf-8"))
        directory = tempfile.TemporaryDirectory()
        connection = connect(str(Path(directory.name) / "index.sqlite"))
        initialize(connection)
        imported = import_file(connection, str(SAMPLE))
        self.assertEqual(imported["candidates"], 2)
        result = query_candidates(
            connection,
            Query(
                graduation_years=(2027,),
                degree_thresholds={"phd": 0},
                venues=("NeurIPS",),
                categories=("main_first",),
                graduation_states=("unknown", "confirmed"),
                strictly_greater=False,
                max_evidence_age_days=None,
            ),
        )
        self.assertEqual(result["confirmed"], [])
        self.assertEqual(result["likely_needs_verification"], [])
        stored = connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        self.assertEqual(stored, 2)
        connection.close()
        directory.cleanup()


if __name__ == "__main__":
    unittest.main()
