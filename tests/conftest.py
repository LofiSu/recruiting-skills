import pytest
from pathlib import Path

from researcher_recruiting.models import (
    AuthorSeed,
    ContactKind,
    ContactPoint,
    ContactStatus,
    Evidence,
    IdentityMatch,
    IdentityState,
    PaperRecord,
    RunResult,
    SourceResult,
    SourceStatus,
)
from researcher_recruiting.config import Settings


@pytest.fixture
def load_fixture():
    def load(name: str) -> str:
        return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")

    return load


@pytest.fixture
def settings(tmp_path):
    return Settings(
        cache_path=tmp_path / "cache.sqlite3",
        user_agent="researcher-recruiting-skill/test",
        github_token=None,
        semantic_scholar_api_key=None,
        openalex_api_key=None,
        ncbi_api_key=None,
        unpaywall_email=None,
        crossref_mailto=None,
        orcid_client_id=None,
        orcid_client_secret=None,
        http_proxy=None,
        https_proxy=None,
        request_timeout_seconds=1,
        max_response_bytes=64,
    )


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
    paper_evidence = evidence_factory(
        field="paper_title", value=paper.title
    )
    contact_points = (
        ContactPoint(
            kind=ContactKind.PROFESSIONAL_EMAIL,
            value="ada@university.example",
            source="university_profile",
            source_url="https://example.test/ada",
            collected_at="2026-07-18T00:00:00Z",
            confidence=95,
            direct=True,
        ),
        ContactPoint(
            kind=ContactKind.CONTACT_FORM,
            value="https://example.test/contact",
            source="university_profile",
            source_url="https://example.test/ada",
            collected_at="2026-07-18T00:00:00Z",
            confidence=90,
            direct=True,
        ),
        ContactPoint(
            kind=ContactKind.GOOGLE_SCHOLAR_LOCATOR,
            value="https://scholar.google.com/scholar?q=Ada+Lovelace",
            source="locator_links",
            source_url="https://scholar.google.com/",
            collected_at="2026-07-18T00:00:00Z",
            confidence=0,
            direct=False,
        ),
        ContactPoint(
            kind=ContactKind.LINKEDIN_LOCATOR,
            value=(
                "https://www.linkedin.com/search/results/people/"
                "?keywords=Ada%20Lovelace"
            ),
            source="locator_links",
            source_url="https://www.linkedin.com/",
            collected_at="2026-07-18T00:00:00Z",
            confidence=0,
            direct=False,
        ),
        ContactPoint(
            kind=ContactKind.MAIMAI_LOCATOR,
            value="https://maimai.cn/search?query=Ada%20Lovelace",
            source="locator_links",
            source_url="https://maimai.cn/",
            collected_at="2026-07-18T00:00:00Z",
            confidence=0,
            direct=False,
        ),
    )
    match = IdentityMatch(
        author=author_seed,
        state=IdentityState.PROBABLE,
        confidence=65,
        reasons=("paper overlap",),
        evidence=(paper_evidence,),
        contact_status=ContactStatus.FOUND,
        contact_points=contact_points,
    )
    source_result = SourceResult(
        source="fixture",
        status=SourceStatus.OK,
        evidence=(paper_evidence,),
        author_name=author_seed.name,
    )
    return RunResult(
        paper=paper,
        matches=(match,),
        source_results=(source_result,),
    )
