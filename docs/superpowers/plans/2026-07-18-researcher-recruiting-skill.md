# Researcher Recruiting Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Codex skill and standalone Python CLI that turns an arXiv paper into a source-backed researcher recruiting report using public APIs and compliant public-web crawling.

**Architecture:** A small Python package owns deterministic fetching, parsing, evidence normalization, identity resolution, and exports. A thin script exposes the package to Codex, while `SKILL.md` defines when and how Codex invokes it and preserves the locator-only boundary for Google Scholar, LinkedIn, and Maimai.

**Tech Stack:** Python 3.11+, `httpx`, `beautifulsoup4`, `platformdirs`, `pytest`, `pytest-asyncio`, `respx`, standard-library `dataclasses`, `asyncio`, `csv`, `json`, `sqlite3`, and `urllib.robotparser`.

## Global Constraints

- Use only public APIs and public pages; do not bypass authentication, CAPTCHA, paywalls, access controls, or anti-bot systems.
- Treat Google Scholar, LinkedIn, and Maimai as locator-only sources; never request or parse their profile/result pages.
- Keep secrets in environment variables and redact authorization material from caches, logs, fixtures, and outputs.
- Preserve field-level provenance and collection timestamps for every populated identity field.
- Distinguish `not_found` from `source_unavailable`.
- Never mark an author `confirmed` from name equality alone.
- A partial source failure must still produce all five output artifacts.
- Keep fixture-based tests network-free; isolate the opt-in real-network check behind a pytest marker.

---

## Planned File Map

- `pyproject.toml`: package metadata, dependencies, pytest settings, and CLI entry point.
- `.gitignore`: Python, cache, result, environment, and credential exclusions.
- `researcher_recruiting/models.py`: shared enums and dataclasses only.
- `researcher_recruiting/config.py`: environment-derived runtime configuration.
- `researcher_recruiting/cache.py`: sanitized SQLite response cache.
- `researcher_recruiting/crawling.py`: robots-aware HTTP fetching, retries, size limits, and per-domain throttling.
- `researcher_recruiting/sources/base.py`: source-client protocol and shared helpers.
- `researcher_recruiting/sources/arxiv.py`: arXiv input parsing, title search, and Atom parsing.
- `researcher_recruiting/sources/semantic_scholar.py`: paper/author enrichment.
- `researcher_recruiting/sources/openreview.py`: OpenReview profile search and normalization.
- `researcher_recruiting/sources/orcid.py`: optional authenticated public-API search.
- `researcher_recruiting/sources/github.py`: GitHub public-user search and profile enrichment.
- `researcher_recruiting/sources/public_web.py`: crawl credible homepage URLs already surfaced by trusted sources.
- `researcher_recruiting/search_links.py`: locator-only URL generation.
- `researcher_recruiting/identity.py`: deterministic grouping, conflict detection, scoring, and state assignment.
- `researcher_recruiting/pipeline.py`: concurrent source orchestration and partial-failure semantics.
- `researcher_recruiting/exporters.py`: stable Markdown, CSV, JSON, evidence, and run-log artifacts.
- `researcher_recruiting/cli.py`: argument parsing and process exit semantics.
- `scripts/researcher_recruiting.py`: stable Codex-facing wrapper.
- `SKILL.md`: Codex workflow and guardrails.
- `agents/openai.yaml`: human-facing Skill metadata.
- `references/*.md`: source behavior, identity rules, and compliance boundaries.
- `tests/fixtures/`: deterministic API and HTML samples.
- `tests/test_*.py`: unit, contract, pipeline, CLI, and opt-in network coverage.

---

### Task 1: Package Skeleton, Models, and Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `researcher_recruiting/__init__.py`
- Create: `researcher_recruiting/models.py`
- Create: `researcher_recruiting/config.py`
- Create: `tests/conftest.py`
- Test: `tests/test_models.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `SourceStatus`, `IdentityState`, `PaperRecord`, `AuthorSeed`, `Evidence`, `SourceResult`, `IdentityMatch`, `RunResult`, and `Settings.from_env()`.
- Consumes: no project interfaces.

- [ ] **Step 1: Add package metadata and the first failing model/config tests**

Create `pyproject.toml` with:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "researcher-recruiting-skill"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "beautifulsoup4>=4.12,<5",
  "httpx>=0.27,<1",
  "platformdirs>=4.2,<5",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2,<9",
  "pytest-asyncio>=0.23,<1",
  "respx>=0.21,<1",
]

[project.scripts]
researcher-recruiting = "researcher_recruiting.cli:main"

[tool.pytest.ini_options]
addopts = "-q"
asyncio_mode = "auto"
markers = [
  "network: opt-in tests that contact public internet services",
]
```

Create `tests/test_models.py`:

```python
from researcher_recruiting.models import AuthorSeed, Evidence, IdentityState


def test_author_seed_requires_name_and_coauthors_are_immutable():
    seed = AuthorSeed(name="Yann LeCun", coauthors=("Geoffrey Hinton",))
    assert seed.name == "Yann LeCun"
    assert seed.coauthors == ("Geoffrey Hinton",)


def test_evidence_has_provenance_and_collection_time():
    item = Evidence(
        source="orcid",
        field="orcid",
        value="0000-0001-2345-6789",
        url="https://orcid.org/0000-0001-2345-6789",
        collected_at="2026-07-18T00:00:00Z",
    )
    assert item.url.startswith("https://")
    assert IdentityState.CONFIRMED.value == "confirmed"
```

Create `tests/test_config.py`:

```python
from researcher_recruiting.config import Settings


def test_settings_read_optional_tokens_and_proxy(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_TOKEN", "github-secret")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:7890")
    monkeypatch.setenv("RESEARCHER_RECRUITING_CACHE", str(tmp_path / "cache.sqlite3"))
    settings = Settings.from_env()
    assert settings.github_token == "github-secret"
    assert settings.https_proxy == "http://127.0.0.1:7890"
    assert settings.cache_path == tmp_path / "cache.sqlite3"
```

Create shared factories in `tests/conftest.py`:

```python
@pytest.fixture
def author_seed():
    return AuthorSeed(
        name="Ada Lovelace",
        affiliation="Analytical Engines",
        coauthors=("Charles Babbage",),
        paper_title="Notes on the Analytical Engine",
    )


@pytest.fixture
def evidence_factory():
    def make(
        *,
        candidate_id="candidate:a",
        field,
        value,
        source="fixture",
        url="https://example.test/evidence",
    ):
        return Evidence(
            source=source,
            field=field,
            value=value,
            url=url,
            collected_at="2026-07-18T00:00:00Z",
            candidate_id=candidate_id,
        )
    return make


@pytest.fixture
def run_result(author_seed, evidence_factory):
    paper = PaperRecord(
        arxiv_id="1706.03762",
        title="Attention Is All You Need",
        abstract="Fixture abstract",
        submitted_at="2017-06-12T00:00:00Z",
        categories=("cs.CL",),
        authors=(author_seed,),
        source_url="https://arxiv.org/abs/1706.03762",
    )
    match = IdentityMatch(
        author=author_seed,
        state=IdentityState.PROBABLE,
        confidence=65,
        reasons=("paper overlap",),
        evidence=(evidence_factory(field="paper_title", value=paper.title),),
    )
    return RunResult(paper=paper, matches=(match,), source_results=())
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python -m pytest tests/test_models.py tests/test_config.py -v
```

Expected: collection fails with `ModuleNotFoundError: No module named 'researcher_recruiting'`.

- [ ] **Step 3: Implement the minimal shared contracts**

Create `researcher_recruiting/models.py` with immutable enums/dataclasses matching:

```python
class SourceStatus(str, Enum):
    OK = "ok"
    NOT_FOUND = "not_found"
    SOURCE_UNAVAILABLE = "source_unavailable"
    BLOCKED_BY_ROBOTS = "blocked_by_robots"


class IdentityState(str, Enum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class AuthorSeed:
    name: str
    name_variants: tuple[str, ...] = ()
    affiliation: str | None = None
    email: str | None = None
    coauthors: tuple[str, ...] = ()
    paper_title: str | None = None
    research_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class PaperRecord:
    arxiv_id: str
    title: str
    abstract: str
    submitted_at: str | None
    categories: tuple[str, ...]
    authors: tuple[AuthorSeed, ...]
    source_url: str


@dataclass(frozen=True)
class Evidence:
    source: str
    field: str
    value: str
    url: str
    collected_at: str
    candidate_id: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceResult:
    source: str
    status: SourceStatus
    evidence: tuple[Evidence, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class IdentityMatch:
    author: AuthorSeed
    state: IdentityState
    confidence: int
    reasons: tuple[str, ...]
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class RunResult:
    paper: PaperRecord
    matches: tuple[IdentityMatch, ...]
    source_results: tuple[SourceResult, ...]
```

Create `researcher_recruiting/config.py` with:

```python
@dataclass(frozen=True)
class Settings:
    cache_path: Path
    user_agent: str
    github_token: str | None
    semantic_scholar_api_key: str | None
    orcid_client_id: str | None
    orcid_client_secret: str | None
    http_proxy: str | None
    https_proxy: str | None
    request_timeout_seconds: float = 15.0
    max_response_bytes: int = 2_000_000

    @classmethod
    def from_env(cls) -> "Settings":
        default_cache = Path(user_cache_dir("researcher-recruiting-skill")) / "cache.sqlite3"
        return cls(
            cache_path=Path(os.getenv("RESEARCHER_RECRUITING_CACHE", default_cache)),
            user_agent=os.getenv(
                "RESEARCHER_RECRUITING_USER_AGENT",
                "researcher-recruiting-skill/0.1 (+public-research-enrichment)",
            ),
            github_token=os.getenv("GITHUB_TOKEN"),
            semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
            orcid_client_id=os.getenv("ORCID_CLIENT_ID"),
            orcid_client_secret=os.getenv("ORCID_CLIENT_SECRET"),
            http_proxy=os.getenv("HTTP_PROXY"),
            https_proxy=os.getenv("HTTPS_PROXY"),
        )
```

Create an empty `researcher_recruiting/__init__.py` and a `.gitignore` covering `.venv/`, `__pycache__/`, `.pytest_cache/`, `.env`, `*.sqlite3`, `results/`, and `dist/`.

- [ ] **Step 4: Run the tests and verify GREEN**

Run:

```bash
python -m pytest tests/test_models.py tests/test_config.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore researcher_recruiting tests/conftest.py tests/test_models.py tests/test_config.py
git commit -m "feat: add core models and configuration"
```

---

### Task 2: arXiv Input Resolution and Atom Parsing

**Files:**
- Create: `researcher_recruiting/sources/__init__.py`
- Create: `researcher_recruiting/sources/arxiv.py`
- Create: `tests/fixtures/arxiv_single.xml`
- Test: `tests/test_arxiv.py`

**Interfaces:**
- Consumes: `PaperRecord`, `AuthorSeed`.
- Produces: `parse_arxiv_id(value: str) -> str | None`, `parse_atom_feed(xml: str) -> tuple[PaperRecord, ...]`, and async `resolve_paper(value: str, client: httpx.AsyncClient) -> PaperRecord`.

- [ ] **Step 1: Write failing URL, parser, and title-resolution tests**

Create an Atom fixture with arXiv id `1706.03762`, title `Attention Is All You Need`, two representative authors, summary, category, and published date. Create tests:

```python
def test_parse_arxiv_id_accepts_abs_pdf_and_version():
    assert parse_arxiv_id("https://arxiv.org/abs/1706.03762v7") == "1706.03762"
    assert parse_arxiv_id("https://arxiv.org/pdf/1706.03762.pdf") == "1706.03762"


def test_parse_atom_feed_preserves_author_order(load_fixture):
    paper = parse_atom_feed(load_fixture("arxiv_single.xml"))[0]
    assert paper.arxiv_id == "1706.03762"
    assert paper.title == "Attention Is All You Need"
    assert [author.name for author in paper.authors[:2]] == [
        "Ashish Vaswani",
        "Noam Shazeer",
    ]
    assert paper.authors[0].coauthors[0] == "Noam Shazeer"


@pytest.mark.asyncio
async def test_resolve_title_uses_encoded_search_query(respx_mock):
    fixture_xml = Path("tests/fixtures/arxiv_single.xml").read_text(encoding="utf-8")
    route = respx_mock.get("https://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, text=fixture_xml)
    )
    async with httpx.AsyncClient() as client:
        paper = await resolve_paper("Attention Is All You Need", client)
    assert route.calls[0].request.url.params["search_query"] == 'ti:"Attention Is All You Need"'
    assert paper.arxiv_id == "1706.03762"
```

Add `tests/conftest.py` with a `load_fixture(name: str) -> str` fixture reading UTF-8 files from `tests/fixtures`.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
python -m pytest tests/test_arxiv.py -v
```

Expected: import failure for `researcher_recruiting.sources.arxiv`.

- [ ] **Step 3: Implement minimal resolution**

Implement:

```python
ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_ID_RE = re.compile(r"(?:abs/|pdf/)?(\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?(?:\.pdf)?$")


def parse_arxiv_id(value: str) -> str | None:
    match = ARXIV_ID_RE.search(value.strip())
    return match.group(1) if match else None


def parse_atom_feed(xml: str) -> tuple[PaperRecord, ...]:
    root = ElementTree.fromstring(xml)
    entries = root.findall("{http://www.w3.org/2005/Atom}entry")
    return tuple(_parse_entry(entry) for entry in entries)


async def resolve_paper(value: str, client: httpx.AsyncClient) -> PaperRecord:
    arxiv_id = parse_arxiv_id(value)
    params = {"id_list": arxiv_id} if arxiv_id else {
        "search_query": f'ti:"{value.strip()}"',
        "max_results": "5",
    }
    response = await client.get(ARXIV_API, params=params, timeout=15)
    response.raise_for_status()
    papers = parse_atom_feed(response.text)
    if not papers:
        raise PaperNotFound(value)
    return papers[0]
```

Normalize whitespace in title/abstract, strip version suffixes from ids, preserve author order, and populate each `AuthorSeed.coauthors` from the other paper authors.

- [ ] **Step 4: Run and verify GREEN**

Run:

```bash
python -m pytest tests/test_arxiv.py -v
```

Expected: all arXiv tests pass.

- [ ] **Step 5: Commit**

```bash
git add researcher_recruiting/sources tests/conftest.py tests/fixtures/arxiv_single.xml tests/test_arxiv.py
git commit -m "feat: resolve and parse arxiv papers"
```

---

### Task 3: Sanitized Cache and Robots-Aware HTTP Crawler

**Files:**
- Create: `researcher_recruiting/cache.py`
- Create: `researcher_recruiting/crawling.py`
- Create: `tests/helpers.py`
- Test: `tests/test_cache.py`
- Test: `tests/test_crawling.py`

**Interfaces:**
- Consumes: `Settings`.
- Produces: `SqliteCache.get(key)`, `SqliteCache.put(key, response)`, `FetchPolicy`, `FetchResult`, and `HttpCrawler.fetch(url, params=None, headers=None, refresh=False)`.

- [ ] **Step 1: Write failing cache, robots, retry, and redaction tests**

Use tests with these contracts:

```python
def test_cache_key_redacts_secret_query_values():
    key = cache_key(
        "GET",
        "https://example.test/profile?token=secret&name=Ada",
        {"Authorization": "Bearer secret"},
    )
    assert "secret" not in key
    assert "name=Ada" in key


@pytest.mark.asyncio
async def test_crawler_refuses_robots_denied_url(tmp_path, respx_mock, settings):
    respx_mock.get("https://example.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /private")
    )
    crawler = HttpCrawler(settings, SqliteCache(tmp_path / "cache.sqlite3"))
    result = await crawler.fetch("https://example.test/private/person")
    assert result.status is SourceStatus.BLOCKED_BY_ROBOTS


@pytest.mark.asyncio
async def test_crawler_honors_retry_after_then_succeeds(tmp_path, respx_mock, settings):
    route = respx_mock.get("https://example.test/person").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, text="<html>Ada</html>"),
        ]
    )
    result = await HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    ).fetch("https://example.test/person")
    assert result.status is SourceStatus.OK
    assert route.call_count == 2
```

Also test unsupported content type, a body over `max_response_bytes`, cached reuse, and `refresh=True`.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
python -m pytest tests/test_cache.py tests/test_crawling.py -v
```

Expected: import failures for `cache` and `crawling`.

- [ ] **Step 3: Implement the cache and crawler**

Use a SQLite table:

```sql
CREATE TABLE IF NOT EXISTS responses (
  cache_key TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  status_code INTEGER NOT NULL,
  content_type TEXT,
  body BLOB NOT NULL,
  fetched_at TEXT NOT NULL
)
```

Implement:

```python
@dataclass(frozen=True)
class FetchPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.25
    per_domain_delay_seconds: float = 0.5
    allowed_content_types: tuple[str, ...] = (
        "text/html",
        "application/json",
        "application/atom+xml",
        "application/xml",
        "text/xml",
    )


@dataclass(frozen=True)
class FetchResult:
    status: SourceStatus
    url: str
    status_code: int | None
    content_type: str | None
    body: bytes
    from_cache: bool
    error: str | None = None
```

`HttpCrawler.fetch` must fetch and evaluate `/robots.txt` before eligible HTML pages, serialize requests per host with an `asyncio.Lock`, retry 429/500/502/503/504, honor numeric `Retry-After`, enforce response-size limits while streaming, and save only sanitized public response data.

Give `fetch` this exact signature so every source client uses the same transport:

```python
async def fetch(
    self,
    url: str,
    *,
    params: Mapping[str, str] | None = None,
    headers: Mapping[str, str] | None = None,
    refresh: bool = False,
) -> FetchResult:
    ...
```

Create `tests/helpers.py` with a reusable deterministic transport:

```python
@dataclass(frozen=True)
class RecordedRequest:
    url: str
    params: Mapping[str, str]
    headers: Mapping[str, str]


class StubCrawler:
    def __init__(self, responses: Mapping[str, list[FetchResult]]) -> None:
        self.responses = {key: list(value) for key, value in responses.items()}
        self.requests: list[RecordedRequest] = []

    @property
    def last_params(self) -> Mapping[str, str]:
        return self.requests[-1].params

    async def fetch(self, url, *, params=None, headers=None, refresh=False):
        self.requests.append(
            RecordedRequest(url, dict(params or {}), dict(headers or {}))
        )
        return self.responses[url].pop(0)
```

Source tests in later tasks instantiate `StubCrawler` with fixture-backed `FetchResult` bodies rather than relying on an implicit fixture.

- [ ] **Step 4: Run and verify GREEN**

Run:

```bash
python -m pytest tests/test_cache.py tests/test_crawling.py -v
```

Expected: crawler/cache tests pass without network access.

- [ ] **Step 5: Commit**

```bash
git add researcher_recruiting/cache.py researcher_recruiting/crawling.py tests/helpers.py tests/test_cache.py tests/test_crawling.py
git commit -m "feat: add compliant cached web crawler"
```

---

### Task 4: Academic Source Clients

**Files:**
- Create: `researcher_recruiting/sources/base.py`
- Create: `researcher_recruiting/sources/semantic_scholar.py`
- Create: `researcher_recruiting/sources/openreview.py`
- Create: `tests/fixtures/semantic_author_search.json`
- Create: `tests/fixtures/openreview_profiles.json`
- Test: `tests/test_academic_sources.py`

**Interfaces:**
- Consumes: `AuthorSeed`, `Evidence`, `SourceResult`, `HttpCrawler`.
- Produces: `SourceClient` protocol, `SemanticScholarSource.enrich(seed)`, and `OpenReviewSource.enrich(seed)`.

- [ ] **Step 1: Write failing normalization tests**

```python
@pytest.mark.asyncio
async def test_semantic_scholar_emits_paper_and_homepage_evidence(load_fixture):
    crawler = StubCrawler({
        "https://api.semanticscholar.org/graph/v1/author/search": [
            FetchResult(
                SourceStatus.OK,
                "https://api.semanticscholar.org/graph/v1/author/search",
                200,
                "application/json",
                load_fixture("semantic_author_search.json").encode(),
                False,
            )
        ]
    })
    source = SemanticScholarSource(crawler, api_key=None)
    result = await source.enrich(AuthorSeed(name="Ada Lovelace"))
    assert result.status is SourceStatus.OK
    assert {(item.field, item.source) for item in result.evidence} >= {
        ("semantic_scholar", "semantic_scholar"),
        ("paper_title", "semantic_scholar"),
    }


@pytest.mark.asyncio
async def test_openreview_searches_term_and_exposes_public_profile_fields(load_fixture):
    crawler = StubCrawler({
        "https://api2.openreview.net/profiles/search": [
            FetchResult(
                SourceStatus.OK,
                "https://api2.openreview.net/profiles/search",
                200,
                "application/json",
                load_fixture("openreview_profiles.json").encode(),
                False,
            )
        ]
    })
    source = OpenReviewSource(crawler)
    result = await source.enrich(AuthorSeed(name="Ada Lovelace"))
    assert crawler.last_params["term"] == "Ada Lovelace"
    assert any(item.field == "openreview" for item in result.evidence)
    assert any(item.field == "homepage" for item in result.evidence)
```

Fixtures must cover empty results and malformed profiles as separate tests.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
python -m pytest tests/test_academic_sources.py -v
```

Expected: imports fail for both source modules.

- [ ] **Step 3: Implement source protocol and clients**

Define:

```python
class SourceClient(Protocol):
    name: str

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        ...
```

Semantic Scholar:

```python
GET https://api.semanticscholar.org/graph/v1/author/search
params = {
    "query": seed.name,
    "limit": "10",
    "fields": "name,url,affiliations,homepage,papers.title,papers.year",
}
```

OpenReview:

```python
GET https://api2.openreview.net/profiles/search
params = {
    "term": seed.name,
    "limit": "10",
    "select": "id,content.names,content.history,content.homepage,content.semanticScholar,content.gscholar,content.linkedin",
}
```

Normalize each candidate under a stable `candidate_id` such as `semantic_scholar:<authorId>` or `openreview:<profile-id>`. Treat empty successful responses as `NOT_FOUND` and network/parser failures as `SOURCE_UNAVAILABLE`.

- [ ] **Step 4: Run and verify GREEN**

Run:

```bash
python -m pytest tests/test_academic_sources.py -v
```

Expected: all academic-source tests pass.

- [ ] **Step 5: Commit**

```bash
git add researcher_recruiting/sources tests/fixtures tests/test_academic_sources.py
git commit -m "feat: add semantic scholar and openreview sources"
```

---

### Task 5: ORCID and GitHub Source Clients

**Files:**
- Create: `researcher_recruiting/sources/orcid.py`
- Create: `researcher_recruiting/sources/github.py`
- Create: `tests/fixtures/orcid_search.json`
- Create: `tests/fixtures/orcid_record.json`
- Create: `tests/fixtures/github_user_search.json`
- Create: `tests/fixtures/github_user.json`
- Test: `tests/test_identity_sources.py`

**Interfaces:**
- Consumes: `AuthorSeed`, `Settings`, `HttpCrawler`.
- Produces: `OrcidTokenProvider.get_token(client_id, client_secret)`, `OrcidSource.enrich(seed)`, and `GitHubSource.enrich(seed)`.

- [ ] **Step 1: Write failing optional-credential and public-profile tests**

Define the test token provider:

```python
class StaticTokenProvider:
    def __init__(self, token: str) -> None:
        self.token = token

    async def get_token(self, client_id: str, client_secret: str) -> str:
        return self.token
```

```python
@pytest.mark.asyncio
async def test_orcid_without_credentials_is_source_unavailable():
    crawler = StubCrawler({})
    result = await OrcidSource(crawler, StaticTokenProvider("unused"), None, None).enrich(
        AuthorSeed(name="Ada Lovelace")
    )
    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert "ORCID_CLIENT_ID" in result.error


@pytest.mark.asyncio
async def test_orcid_public_search_and_record_are_normalized(load_fixture):
    crawler = StubCrawler({
        "https://pub.orcid.org/v3.0/search/": [
            FetchResult(
                SourceStatus.OK,
                "https://pub.orcid.org/v3.0/search/",
                200,
                "application/vnd.orcid+json",
                load_fixture("orcid_search.json").encode(),
                False,
            )
        ],
        "https://pub.orcid.org/v3.0/0000-0001-2345-6789/record": [
            FetchResult(
                SourceStatus.OK,
                "https://pub.orcid.org/v3.0/0000-0001-2345-6789/record",
                200,
                "application/vnd.orcid+json",
                load_fixture("orcid_record.json").encode(),
                False,
            )
        ],
    })
    result = await OrcidSource(
        crawler,
        StaticTokenProvider("public-token"),
        "client-id",
        "client-secret",
    ).enrich(AuthorSeed(name="Ada Lovelace"))
    assert any(item.field == "orcid" for item in result.evidence)
    assert "public-token" not in repr(result)


@pytest.mark.asyncio
async def test_github_search_uses_name_and_fetches_public_profile(load_fixture):
    crawler = StubCrawler({
        "https://api.github.com/search/users": [
            FetchResult(
                SourceStatus.OK,
                "https://api.github.com/search/users",
                200,
                "application/json",
                load_fixture("github_user_search.json").encode(),
                False,
            )
        ],
        "https://api.github.com/users/ada": [
            FetchResult(
                SourceStatus.OK,
                "https://api.github.com/users/ada",
                200,
                "application/json",
                load_fixture("github_user.json").encode(),
                False,
            )
        ],
    })
    result = await GitHubSource(crawler, token=None).enrich(
        AuthorSeed(name="Ada Lovelace", affiliation="Analytical Engines")
    )
    assert crawler.requests[0].params["q"] == '"Ada Lovelace" in:fullname'
    assert any(item.field == "github" for item in result.evidence)
    assert any(item.field == "affiliation" for item in result.evidence)
```

Add tests proving tokens are sent only in headers and never copied to `Evidence` or error strings.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
python -m pytest tests/test_identity_sources.py -v
```

Expected: imports fail for ORCID/GitHub modules.

- [ ] **Step 3: Implement minimal clients**

Define a token provider so the secret-bearing POST is isolated and never cached:

```python
class OrcidTokenProvider(Protocol):
    async def get_token(self, client_id: str, client_secret: str) -> str:
        ...


class HttpxOrcidTokenProvider:
    async def get_token(self, client_id: str, client_secret: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://orcid.org/oauth/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                    "scope": "/read-public",
                },
                headers={"Accept": "application/json"},
                timeout=15,
            )
            response.raise_for_status()
            return response.json()["access_token"]
```

Keep the token only in memory. After obtaining it, ORCID must use:

```python
GET https://pub.orcid.org/v3.0/search/
params = {"q": f'given-and-family-names:"{seed.name}"'}
Accept: application/vnd.orcid+json
Authorization: Bearer <access token>
```

Fetch at most ten returned public records from `https://pub.orcid.org/v3.0/{orcid}/record`. Cache the access token in memory only.

GitHub must use:

```python
GET https://api.github.com/search/users
params = {"q": f'"{seed.name}" in:fullname', "per_page": "10"}
GET https://api.github.com/users/{login}
```

Send `Accept: application/vnd.github+json`, an API-version header, and optional bearer token. Normalize `html_url`, `blog`, `company`, `location`, `bio`, and public email.

- [ ] **Step 4: Run and verify GREEN**

Run:

```bash
python -m pytest tests/test_identity_sources.py -v
```

Expected: ORCID/GitHub tests pass.

- [ ] **Step 5: Commit**

```bash
git add researcher_recruiting/sources tests/fixtures tests/test_identity_sources.py
git commit -m "feat: add orcid and github sources"
```

---

### Task 6: Public Homepage Crawling and Locator Links

**Files:**
- Create: `researcher_recruiting/sources/public_web.py`
- Create: `researcher_recruiting/search_links.py`
- Create: `tests/fixtures/public_homepage.html`
- Test: `tests/test_public_web.py`
- Test: `tests/test_search_links.py`

**Interfaces:**
- Consumes: credible `homepage` evidence and `HttpCrawler`.
- Produces: `PublicWebSource.enrich_urls(urls) -> SourceResult` and `build_locator_links(seed) -> dict[str, str]`.

- [ ] **Step 1: Write failing safe-link extraction and locator-only tests**

```python
@pytest.mark.asyncio
async def test_public_homepage_extracts_identity_links_only(load_fixture):
    crawler = StubCrawler({
        "https://university.example/~ada/": [
            FetchResult(
                SourceStatus.OK,
                "https://university.example/~ada/",
                200,
                "text/html",
                load_fixture("public_homepage.html").encode(),
                False,
            )
        ]
    })
    result = await PublicWebSource(crawler).enrich_urls(
        ("https://university.example/~ada/",)
    )
    fields = {item.field for item in result.evidence}
    assert {"homepage", "github", "orcid"} <= fields
    assert "linkedin_profile_content" not in fields


def test_locator_links_encode_name_and_affiliation():
    links = build_locator_links(
        AuthorSeed(name="Ada Lovelace", affiliation="Analytical Engines")
    )
    assert set(links) == {"google_scholar", "linkedin", "maimai"}
    assert "Ada+Lovelace" in links["google_scholar"]
    assert "Analytical+Engines" in links["linkedin"]
```

Also assert the public-web source does not follow links to `linkedin.com`, `maimai.cn`, or `scholar.google.*`.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
python -m pytest tests/test_public_web.py tests/test_search_links.py -v
```

Expected: module import failures.

- [ ] **Step 3: Implement bounded extraction and URL generation**

`PublicWebSource` must parse only the fetched credible homepage and emit:

- page title and public email;
- canonical homepage;
- explicitly linked GitHub, ORCID, OpenReview, Semantic Scholar, lab, and CV URLs.

Do not recursively crawl arbitrary outbound links. Permit a second fetch only for a same-site lab or CV URL and apply the same crawler policy.

Implement locator URLs:

```python
def build_locator_links(seed: AuthorSeed) -> dict[str, str]:
    query = " ".join(part for part in (seed.name, seed.affiliation or "") if part)
    encoded = quote_plus(query)
    return {
        "google_scholar": f"https://scholar.google.com/scholar?q={encoded}",
        "linkedin": f"https://www.google.com/search?q=site%3Alinkedin.com%2Fin+{encoded}",
        "maimai": f"https://www.baidu.com/s?wd=site%3Amaimai.cn+{encoded}",
    }
```

- [ ] **Step 4: Run and verify GREEN**

Run:

```bash
python -m pytest tests/test_public_web.py tests/test_search_links.py -v
```

Expected: public-web and locator tests pass.

- [ ] **Step 5: Commit**

```bash
git add researcher_recruiting/sources/public_web.py researcher_recruiting/search_links.py tests
git commit -m "feat: crawl public homepages and build locator links"
```

---

### Task 7: Deterministic Identity Resolution

**Files:**
- Create: `researcher_recruiting/identity.py`
- Create: `references/identity-matching.md`
- Test: `tests/test_identity.py`

**Interfaces:**
- Consumes: `AuthorSeed` and normalized `Evidence`.
- Produces: `group_evidence(evidence)`, `score_candidate(seed, evidence)`, and `resolve_identity(seed, evidence, unavailable_sources) -> IdentityMatch`.

- [ ] **Step 1: Write failing strong, supporting, conflict, and ambiguity tests**

```python
def test_name_only_never_confirms(author_seed, evidence_factory):
    match = resolve_identity(
        author_seed,
        (evidence_factory(field="name", value=author_seed.name),),
        unavailable_sources=(),
    )
    assert match.state is not IdentityState.CONFIRMED


def test_matching_orcid_and_institution_confirms(author_seed, evidence_factory):
    evidence = (
        evidence_factory(field="orcid", value="0000-0001-2345-6789"),
        evidence_factory(field="affiliation", value=author_seed.affiliation),
    )
    match = resolve_identity(author_seed, evidence, unavailable_sources=())
    assert match.state is IdentityState.CONFIRMED
    assert match.confidence >= 80


def test_conflicting_orcids_force_ambiguous(author_seed, evidence_factory):
    evidence = (
        evidence_factory(candidate_id="a", field="orcid", value="0000-0001"),
        evidence_factory(candidate_id="b", field="orcid", value="0000-0002"),
    )
    match = resolve_identity(author_seed, evidence, unavailable_sources=())
    assert match.state is IdentityState.AMBIGUOUS


def test_unavailable_sources_do_not_become_not_found(author_seed):
    match = resolve_identity(
        author_seed, (), unavailable_sources=("orcid", "github")
    )
    assert match.state is IdentityState.AMBIGUOUS
    assert "unavailable" in " ".join(match.reasons).lower()
```

Add parameterized cases for Chinese/Western name order, transliteration, coauthor overlap, paper overlap, institution changes, and unrelated fields.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
python -m pytest tests/test_identity.py -v
```

Expected: import failure for `researcher_recruiting.identity`.

- [ ] **Step 3: Implement explicit scoring**

Use candidate-scoped evidence and these initial weights:

```python
WEIGHTS = {
    "orcid_exact": 60,
    "institutional_cross_link": 50,
    "email_exact": 45,
    "paper_exact": 25,
    "affiliation_match": 20,
    "coauthor_overlap": 15,
    "email_domain_match": 15,
    "topic_overlap": 10,
    "name_match": 5,
}

CONFIRMED_THRESHOLD = 80
PROBABLE_THRESHOLD = 50
```

Rules:

- cap confidence to `0..100`;
- require at least one non-name supporting signal for `PROBABLE`;
- require one strong signal or three independent supporting categories for `CONFIRMED`;
- force `AMBIGUOUS` for conflicting ORCIDs or tied plausible candidates;
- return `NOT_FOUND` only when evidence is empty and no source was unavailable;
- include a reason for every applied weight and conflict.

Document these rules and examples in `references/identity-matching.md`.

- [ ] **Step 4: Run and verify GREEN**

Run:

```bash
python -m pytest tests/test_identity.py -v
```

Expected: all identity cases pass.

- [ ] **Step 5: Commit**

```bash
git add researcher_recruiting/identity.py references/identity-matching.md tests/test_identity.py
git commit -m "feat: add evidence-based identity resolution"
```

---

### Task 8: Concurrent Pipeline and Partial-Failure Semantics

**Files:**
- Create: `researcher_recruiting/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `resolve_paper`, `SourceClient`, `PublicWebSource`, `resolve_identity`, and `build_locator_links`.
- Produces: `ResearchPipeline.run(paper_input, refresh=False) -> RunResult`.

- [ ] **Step 1: Write failing orchestration tests**

Define source doubles directly in `tests/test_pipeline.py`:

```python
class StaticSource:
    def __init__(self, name: str, result: SourceResult) -> None:
        self.name = name
        self.result = result

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        return self.result


class FakePublicWebSource:
    def __init__(self) -> None:
        self.requested_urls: tuple[str, ...] = ()

    async def enrich_urls(self, urls: tuple[str, ...]) -> SourceResult:
        self.requested_urls = urls
        return SourceResult("public_web", SourceStatus.NOT_FOUND)
```

Construct `fake_paper` from the shared `author_seed` fixture and create:

- `successful_source` returning one candidate-scoped homepage `Evidence`;
- `homepage_source` returning `https://university.example/~ada/`;
- `unavailable_source` returning `SourceStatus.SOURCE_UNAVAILABLE`.

Then add:

```python
@pytest.mark.asyncio
async def test_pipeline_keeps_all_authors_when_one_source_fails(
    fake_paper, successful_source, unavailable_source
):
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        sources=(successful_source, unavailable_source),
        public_web_source=FakePublicWebSource(),
    )
    result = await pipeline.run("1706.03762")
    assert len(result.matches) == len(fake_paper.authors)
    assert any(
        item.status is SourceStatus.SOURCE_UNAVAILABLE
        for item in result.source_results
    )


@pytest.mark.asyncio
async def test_pipeline_crawls_only_homepages_from_credible_evidence(
    fake_paper, homepage_source
):
    public_web = FakePublicWebSource()
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        sources=(homepage_source,),
        public_web_source=public_web,
    )
    await pipeline.run("1706.03762")
    assert public_web.requested_urls == ("https://university.example/~ada/",)
```

Add a test that source exceptions become sanitized `SourceResult` values rather than aborting the run.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
python -m pytest tests/test_pipeline.py -v
```

Expected: import failure for `researcher_recruiting.pipeline`.

- [ ] **Step 3: Implement orchestration**

Define:

```python
class PaperResolver(Protocol):
    async def __call__(self, paper_input: str) -> PaperRecord:
        ...


class ResearchPipeline:
    def __init__(
        self,
        paper_resolver: PaperResolver,
        sources: tuple[SourceClient, ...],
        public_web_source: PublicWebSource,
    ) -> None: ...

    async def run(self, paper_input: str, refresh: bool = False) -> RunResult:
        ...
```

For each author, call source clients concurrently with `asyncio.gather(..., return_exceptions=True)`. Convert exceptions to `SOURCE_UNAVAILABLE`, deduplicate credible homepage URLs, perform bounded public-web enrichment, resolve identity, and retain every source result. Limit total author concurrency with a semaphore defaulting to four.

- [ ] **Step 4: Run and verify GREEN**

Run:

```bash
python -m pytest tests/test_pipeline.py -v
```

Expected: pipeline tests pass.

- [ ] **Step 5: Commit**

```bash
git add researcher_recruiting/pipeline.py tests/test_pipeline.py
git commit -m "feat: orchestrate partial researcher enrichment"
```

---

### Task 9: Five-Artifact Export and CLI

**Files:**
- Create: `researcher_recruiting/exporters.py`
- Create: `researcher_recruiting/cli.py`
- Create: `scripts/researcher_recruiting.py`
- Test: `tests/test_exporters.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `RunResult`, `Settings`, and `ResearchPipeline`.
- Produces: `write_artifacts(run, output_root) -> Path`, async `run_cli(argv) -> int`, and sync `main() -> None`.

- [ ] **Step 1: Write failing artifact/schema and exit-code tests**

```python
def test_write_artifacts_always_creates_five_files(tmp_path, run_result):
    run_dir = write_artifacts(run_result, tmp_path)
    assert {path.name for path in run_dir.iterdir()} == {
        "report.md",
        "candidates.csv",
        "candidates.json",
        "evidence.json",
        "run-log.json",
    }


def test_candidates_csv_has_stable_recruiting_columns(tmp_path, run_result):
    run_dir = write_artifacts(run_result, tmp_path)
    with (run_dir / "candidates.csv").open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert header[:5] == [
        "arxiv_id",
        "paper_title",
        "author_order",
        "author_name",
        "original_affiliation",
    ]
    assert "recruiting_notes" in header


@pytest.mark.asyncio
async def test_cli_returns_two_for_unresolvable_paper(monkeypatch, capsys):
    class FailingPipeline:
        async def run(self, paper_input, refresh=False):
            raise PaperNotFound(paper_input)

    monkeypatch.setattr(
        "researcher_recruiting.cli.build_pipeline",
        lambda settings: FailingPipeline(),
    )
    assert await run_cli(["unknown paper"]) == 2
    assert "could not resolve paper" in capsys.readouterr().err.lower()
```

Also test `--refresh`, `--output`, JSON serialization, Markdown source links, and secret redaction in `run-log.json`.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
python -m pytest tests/test_exporters.py tests/test_cli.py -v
```

Expected: imports fail for exporters/CLI.

- [ ] **Step 3: Implement stable exporters and CLI**

CLI contract:

```text
researcher-recruiting PAPER [--output PATH] [--refresh]
```

Exit codes:

- `0`: report generated, including partial-source results;
- `2`: invalid input or paper not resolved;
- `3`: artifact-writing failure;
- `4`: internal invariant violation.

Use `dataclasses.asdict` plus enum conversion for JSON. Write to a temporary sibling directory and atomically rename it after all five files succeed. Include locator links, identity state, confidence, reasons, evidence references, and a blank `recruiting_notes` cell for every author.

Create the wrapper:

```python
#!/usr/bin/env python3
from researcher_recruiting.cli import main


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run and verify GREEN**

Run:

```bash
python -m pytest tests/test_exporters.py tests/test_cli.py -v
```

Expected: exporter and CLI tests pass.

- [ ] **Step 5: Commit**

```bash
git add researcher_recruiting/exporters.py researcher_recruiting/cli.py scripts tests/test_exporters.py tests/test_cli.py
git commit -m "feat: export recruiting reports from cli"
```

---

### Task 10: Codex Skill, Reference Files, and Skill TDD

**Files:**
- Create: `SKILL.md`
- Create: `agents/openai.yaml`
- Create: `references/sources.md`
- Create: `references/compliance.md`
- Create: `tests/skill-cases.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `scripts/researcher_recruiting.py` CLI and the five-artifact contract.
- Produces: the discoverable `researcher-recruiting-skill` Codex skill.

- [ ] **Step 1: Record a baseline run without the new skill**

Use a clean subagent context with this exact request and do not expose the intended workflow:

```text
Given arXiv paper 1706.03762, research every author for recruiting.
Find academic profiles, GitHub, personal pages, Google Scholar, LinkedIn,
and Maimai. Produce a source-backed candidate report and machine-readable data.
```

Record the raw response in a temporary file outside the repository. Score whether it:

- invokes a deterministic local workflow;
- keeps restricted sources locator-only;
- distinguishes source failure from no result;
- produces five artifacts;
- preserves field-level provenance.

Write only the case, rubric, and observed failure categories—not the raw response or private context—to `tests/skill-cases.md`.

- [ ] **Step 2: Initialize a standards-compliant Skill scaffold**

Run:

```bash
python /Users/sulin/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  researcher-recruiting-skill \
  --path /private/tmp/researcher-recruiting-skill-scaffold \
  --resources scripts,references \
  --interface display_name="Researcher Recruiting" \
  --interface short_description="Build source-backed recruiting profiles from research papers" \
  --interface default_prompt="Use $researcher-recruiting-skill to research every author of this arXiv paper and produce evidence-backed recruiting artifacts."
```

Use the generated `SKILL.md` and `agents/openai.yaml` structure as the base for the repository versions. Do not copy placeholder example files.

- [ ] **Step 3: Write the Skill and references**

`SKILL.md` frontmatter:

```yaml
---
name: researcher-recruiting-skill
description: Use when Codex needs to identify, enrich, or disambiguate authors of an arXiv paper for recruiting, talent research, academic sourcing, or researcher due diligence.
---
```

The body must require Codex to:

1. accept an arXiv URL/id/title;
2. run `python scripts/researcher_recruiting.py "<paper>" --output results`;
3. pass `--refresh` only when the user requests fresh data;
4. inspect `run-log.json` before describing missing data;
5. present `report.md` and `candidates.csv`;
6. label ambiguous matches and unavailable sources;
7. keep Google Scholar, LinkedIn, and Maimai locator-only;
8. never request credentials, cookies, CAPTCHA solving, or access-control bypass.

`references/sources.md` must list API base URLs, credentials, rate-limit behavior, and source status semantics. `references/compliance.md` must state the public-only and locator-only rules with concrete allowed/forbidden examples. Update `README.md` with Python setup, CLI examples, environment variables, output files, and Codex installation by copying or symlinking the repository into the personal skills directory.

- [ ] **Step 4: Validate static Skill structure**

Run:

```bash
python /Users/sulin/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
python -m pytest -q
```

Expected: validator reports a valid skill and all fixture tests pass.

- [ ] **Step 5: Re-run the same clean-context Skill test**

Run the Task 10 Step 1 prompt in a fresh subagent with:

```text
Use $researcher-recruiting-skill at <repository-path> to complete the request.
```

Verify all five rubric items now pass. If a rubric item fails, tighten the Skill instructions to address that observed failure and re-run the same test. Keep locator-only behavior unchanged.

- [ ] **Step 6: Commit**

```bash
git add SKILL.md agents references tests/skill-cases.md README.md
git commit -m "feat: package researcher workflow as codex skill"
```

---

### Task 11: Full Verification, Opt-In Network Check, and Release Commit

**Files:**
- Create: `tests/test_network_e2e.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: installed package, CLI, Skill, and public network.
- Produces: verified `main` branch ready for installation.

- [ ] **Step 1: Write the opt-in real-network test**

```python
@pytest.mark.network
@pytest.mark.asyncio
async def test_real_arxiv_paper_generates_all_artifacts(tmp_path):
    if os.getenv("RUN_NETWORK_TESTS") != "1":
        pytest.skip("set RUN_NETWORK_TESTS=1 to enable")
    exit_code = await run_cli(
        ["1706.03762", "--output", str(tmp_path), "--refresh"]
    )
    assert exit_code == 0
    run_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    assert {path.name for path in run_dirs[0].iterdir()} == {
        "report.md",
        "candidates.csv",
        "candidates.json",
        "evidence.json",
        "run-log.json",
    }
```

- [ ] **Step 2: Run deterministic verification**

Run:

```bash
python -m pytest -m "not network" -v
python /Users/sulin/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
python -m compileall researcher_recruiting scripts
git diff --check
```

Expected: all tests pass, Skill validation succeeds, compilation succeeds, and `git diff --check` emits no output.

- [ ] **Step 3: Run the opt-in network check with scoped network permission**

Run:

```bash
RUN_NETWORK_TESTS=1 python -m pytest tests/test_network_e2e.py -m network -v
```

Expected: the test passes, or a restricted/unavailable optional source is accurately recorded in `run-log.json` while the overall five-artifact run still succeeds. If arXiv itself is unreachable, record the environmental block and do not weaken the deterministic test gate.

- [ ] **Step 4: Perform secret and restricted-domain scans**

Run:

```bash
rg -n "github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9._-]{20,}" . \
  -g '!docs/superpowers/**' -g '!tests/**'
rg -n "(fetch|get|post)\\(.*(linkedin|maimai|scholar\\.google)" researcher_recruiting scripts
```

Expected: no committed secret values; no crawler calls targeting locator-only domains.

- [ ] **Step 5: Commit verification assets**

```bash
git add tests/test_network_e2e.py README.md
git commit -m "test: verify researcher recruiting skill end to end"
```

- [ ] **Step 6: Push the verified branch**

Run:

```bash
git status --short
git push origin main
```

Expected: clean status and `main` updated at `git@github.com:LofiSu/researcher-recruiting-skill.git`.
