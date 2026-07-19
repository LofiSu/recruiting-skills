import pytest

from researcher_recruiting.crawling import FetchResult
from researcher_recruiting.models import SourceStatus
from researcher_recruiting.sources.public_web import PublicWebSource
from tests.helpers import StubCrawler


def html_result(url, html):
    return FetchResult(
        SourceStatus.OK,
        url,
        200,
        "text/html",
        html.encode(),
        False,
    )


@pytest.mark.asyncio
async def test_public_homepage_extracts_identity_links_only(load_fixture):
    url = "https://university.example/~ada/"
    crawler = StubCrawler(
        {
            url: [
                html_result(url, load_fixture("public_homepage.html"))
            ]
        }
    )
    enriched = await PublicWebSource(crawler).enrich_urls((url,))
    fields = {item.field for item in enriched.evidence}
    assert {
        "homepage",
        "github",
        "orcid",
        "openreview",
        "semantic_scholar",
        "email",
        "contact_form",
    } <= fields
    assert "linkedin" not in fields
    assert "maimai" not in fields
    assert not any(
        item.value == "https://external.example/contact"
        for item in enriched.evidence
    )
    assert crawler.requests == [crawler.requests[0]]


@pytest.mark.asyncio
async def test_public_homepage_normalizes_email_and_finds_contact_form():
    url = "https://university.example/~ada/"
    html = (
        '<a href="mailto:%20Ada@Example.org?subject=Research">'
        "Email</a>"
        '<a href="/contact/">Contact Ada</a>'
        '<a href="https://external.example/contact">External contact</a>'
    )
    crawler = StubCrawler({url: [html_result(url, html)]})
    result = await PublicWebSource(crawler).enrich_urls((url,))
    email = next(item for item in result.evidence if item.field == "email")
    form = next(
        item for item in result.evidence if item.field == "contact_form"
    )
    assert email.value == "ada@example.org"
    assert email.metadata["visibility"] == "public_professional"
    assert form.value == "https://university.example/contact/"
    assert not any(
        item.value == "https://external.example/contact"
        for item in result.evidence
    )


@pytest.mark.asyncio
async def test_public_homepage_follows_only_one_same_site_lab_page():
    home = "https://university.example/~ada/"
    lab = "https://university.example/lab/"
    home_html = (
        '<a href="/lab/">Lab</a>'
        '<a href="https://external.example/lab/">Other lab</a>'
        '<a href="https://linkedin.com/in/ada">LinkedIn</a>'
    )
    lab_html = '<a href="mailto:lab@university.example">Lab email</a>'
    crawler = StubCrawler(
        {
            home: [html_result(home, home_html)],
            lab: [html_result(lab, lab_html)],
        }
    )
    enriched = await PublicWebSource(crawler).enrich_urls((home,))
    assert [request.url for request in crawler.requests] == [home, lab]
    assert any(
        item.field == "email" and item.value == "lab@university.example"
        for item in enriched.evidence
    )


@pytest.mark.asyncio
async def test_public_homepage_rejects_local_network_urls_without_fetch():
    crawler = StubCrawler({})
    enriched = await PublicWebSource(crawler).enrich_urls(
        ("http://127.0.0.1/private", "http://localhost/admin")
    )
    assert enriched.status is SourceStatus.NOT_FOUND
    assert crawler.requests == []
