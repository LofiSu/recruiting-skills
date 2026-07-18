import pytest
from pathlib import Path

from researcher_recruiting.models import (
    AuthorSeed,
    Evidence,
    IdentityMatch,
    IdentityState,
    PaperRecord,
    RunResult,
)


@pytest.fixture
def load_fixture():
    def load(name: str) -> str:
        return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")

    return load


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
