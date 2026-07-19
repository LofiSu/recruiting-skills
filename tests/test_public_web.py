import socket

import httpx
import pytest

from researcher_recruiting.cache import SqliteCache
from researcher_recruiting.crawling import HttpCrawler
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


@pytest.mark.asyncio
async def test_public_homepage_rejects_restricted_sites_without_fetch():
    urls = (
        "https://scholar.google.com/citations?user=ada",
        "https://www.researchgate.net/profile/Ada-Lovelace",
        "https://academia.edu/AdaLovelace",
        "https://www.linkedin.com/in/ada-lovelace",
        "https://maimai.cn/contact/detail/123",
        "https://www.scopus.com/authid/detail.uri?authorId=123",
        "https://www.webofscience.com/wos/author/record/123",
        "https://app.dimensions.ai/discover/publication",
        "https://www.lens.org/lens/profile/123",
        "https://ui.adsabs.harvard.edu/search/q=author%3Aada",
        "https://ieeexplore.ieee.org/author/123",
        "https://link.springer.com/search?query=ada",
    )
    crawler = StubCrawler(
        {url: [html_result(url, "<p>Restricted</p>")] for url in urls}
    )

    enriched = await PublicWebSource(crawler).enrich_urls(urls)

    assert enriched.status is SourceStatus.NOT_FOUND
    assert crawler.requests == []


def _public_dns(host, port, *args, **kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("93.184.216.34", port),
        )
    ]


_PINNED_PUBLIC_ORIGIN = "https://93.184.216.34"


@pytest.mark.asyncio
async def test_public_homepage_does_not_follow_redirect_to_restricted_site(
    tmp_path, respx_mock, settings, monkeypatch
):
    monkeypatch.setattr(socket, "getaddrinfo", _public_dns)
    respx_mock.get(f"{_PINNED_PUBLIC_ORIGIN}/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /")
    )
    respx_mock.get(f"{_PINNED_PUBLIC_ORIGIN}/person").mock(
        return_value=httpx.Response(
            302,
            headers={
                "Location": "https://www.researchgate.net/profile/Ada"
            },
        )
    )
    restricted_robots = respx_mock.get(
        "https://www.researchgate.net/robots.txt"
    ).mock(return_value=httpx.Response(200, text="User-agent: *\nAllow: /"))
    restricted = respx_mock.get(
        "https://www.researchgate.net/profile/Ada"
    ).mock(return_value=httpx.Response(200, text="<html>secret</html>"))
    crawler = HttpCrawler(settings, SqliteCache(tmp_path / "cache.sqlite3"))

    result = await PublicWebSource(crawler).enrich_urls(
        ("https://safe.example/person",)
    )

    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert restricted_robots.call_count == 0
    assert restricted.call_count == 0


@pytest.mark.asyncio
async def test_public_homepage_does_not_follow_redirect_to_loopback(
    tmp_path, respx_mock, settings, monkeypatch
):
    monkeypatch.setattr(socket, "getaddrinfo", _public_dns)
    respx_mock.get(f"{_PINNED_PUBLIC_ORIGIN}/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /")
    )
    respx_mock.get(f"{_PINNED_PUBLIC_ORIGIN}/person").mock(
        return_value=httpx.Response(
            302, headers={"Location": "http://127.0.0.1/admin"}
        )
    )
    loopback = respx_mock.get("http://127.0.0.1/admin").mock(
        return_value=httpx.Response(200, text="<html>secret</html>")
    )
    crawler = HttpCrawler(settings, SqliteCache(tmp_path / "cache.sqlite3"))

    result = await PublicWebSource(crawler).enrich_urls(
        ("https://safe.example/person",)
    )

    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert loopback.call_count == 0


@pytest.mark.asyncio
async def test_public_homepage_does_not_follow_dns_to_private_address(
    tmp_path, respx_mock, settings, monkeypatch
):
    def dns(host, port, *args, **kwargs):
        if host == "private.example":
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    socket.IPPROTO_TCP,
                    "",
                    ("10.0.0.8", port),
                )
            ]
        return _public_dns(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", dns)
    respx_mock.get(f"{_PINNED_PUBLIC_ORIGIN}/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /")
    )
    respx_mock.get(f"{_PINNED_PUBLIC_ORIGIN}/person").mock(
        return_value=httpx.Response(
            302, headers={"Location": "https://private.example/admin"}
        )
    )
    private_robots = respx_mock.get(
        "https://private.example/robots.txt"
    ).mock(return_value=httpx.Response(200, text="User-agent: *\nAllow: /"))
    private = respx_mock.get("https://private.example/admin").mock(
        return_value=httpx.Response(200, text="<html>secret</html>")
    )
    crawler = HttpCrawler(settings, SqliteCache(tmp_path / "cache.sqlite3"))

    result = await PublicWebSource(crawler).enrich_urls(
        ("https://safe.example/person",)
    )

    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert private_robots.call_count == 0
    assert private.call_count == 0


@pytest.mark.asyncio
async def test_public_homepage_allows_public_redirect_with_per_hop_robots(
    tmp_path, respx_mock, settings, monkeypatch
):
    monkeypatch.setattr(socket, "getaddrinfo", _public_dns)
    robots = respx_mock.get(
        f"{_PINNED_PUBLIC_ORIGIN}/robots.txt"
    ).mock(return_value=httpx.Response(200, text="User-agent: *\nAllow: /"))
    respx_mock.get(f"{_PINNED_PUBLIC_ORIGIN}/person").mock(
        return_value=httpx.Response(
            302, headers={"Location": "https://public.example/final"}
        )
    )
    respx_mock.get(f"{_PINNED_PUBLIC_ORIGIN}/final").mock(
        return_value=httpx.Response(200, text="<title>Ada</title>")
    )
    crawler = HttpCrawler(settings, SqliteCache(tmp_path / "cache.sqlite3"))

    result = await PublicWebSource(crawler).enrich_urls(
        ("https://safe.example/person",)
    )

    assert result.status is SourceStatus.OK
    homepage = next(
        item for item in result.evidence if item.field == "homepage"
    )
    assert homepage.value == "https://public.example/final"
    assert homepage.url == "https://public.example/final"
    assert robots.call_count == 2


@pytest.mark.asyncio
async def test_public_homepage_pins_one_validated_resolution_per_hop(
    tmp_path, settings, monkeypatch
):
    resolution_calls = []

    def rebinding_dns(host, port, *args, **kwargs):
        resolution_calls.append((host, port))
        address = (
            "93.184.216.34"
            if len(resolution_calls) == 1
            else "127.0.0.1"
        )
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (address, port),
            )
        ]

    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, text="User-agent: *\nAllow: /", request=request
            )
        return httpx.Response(
            200, text="<title>Ada</title>", request=request
        )

    def direct_client(_crawler, *, direct=False):
        assert direct is True
        return httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=False,
            trust_env=False,
        )

    monkeypatch.setattr(socket, "getaddrinfo", rebinding_dns)
    monkeypatch.setattr(HttpCrawler, "_client", direct_client)
    crawler = HttpCrawler(settings, SqliteCache(tmp_path / "cache.sqlite3"))

    result = await PublicWebSource(crawler).enrich_urls(
        ("https://safe.example/person",)
    )

    assert result.status is SourceStatus.OK
    assert resolution_calls == [("safe.example", 443)]
    assert [request.url.host for request in requests] == [
        "93.184.216.34",
        "93.184.216.34",
    ]
    assert [request.headers["Host"] for request in requests] == [
        "safe.example",
        "safe.example",
    ]
    assert [request.extensions["sni_hostname"] for request in requests] == [
        "safe.example",
        "safe.example",
    ]


@pytest.mark.asyncio
async def test_public_homepage_rejects_cgnat_and_mapped_private_literals():
    cgnat = "http://100.64.0.1/person"
    crawler = StubCrawler(
        {cgnat: [html_result(cgnat, "<title>unsafe</title>")]}
    )

    result = await PublicWebSource(crawler).enrich_urls(
        (
            cgnat,
            "http://[::ffff:127.0.0.1]/person",
        )
    )

    assert result.status is SourceStatus.NOT_FOUND
    assert crawler.requests == []


@pytest.mark.asyncio
async def test_public_homepage_rejects_mixed_dns_with_non_global_address(
    tmp_path, settings, monkeypatch
):
    def mixed_dns(host, port, *args, **kwargs):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", port),
            ),
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("fd00::1", port, 0, 0),
            ),
        ]

    client_created = False

    def forbidden_client(_crawler, *, direct=False):
        nonlocal client_created
        client_created = True
        return httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, text="User-agent: *\nAllow: /", request=request
                )
            ),
            follow_redirects=False,
            trust_env=False,
        )

    monkeypatch.setattr(socket, "getaddrinfo", mixed_dns)
    monkeypatch.setattr(HttpCrawler, "_client", forbidden_client)
    crawler = HttpCrawler(settings, SqliteCache(tmp_path / "cache.sqlite3"))

    result = await PublicWebSource(crawler).enrich_urls(
        ("https://mixed.example/person",)
    )

    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert client_created is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "destination",
    (
        "https://www.researchgate.net/robots.txt",
        "http://127.0.0.1/robots.txt",
    ),
)
async def test_public_homepage_blocks_unsafe_robots_redirect(
    tmp_path, respx_mock, settings, monkeypatch, destination
):
    monkeypatch.setattr(socket, "getaddrinfo", _public_dns)
    respx_mock.get(f"{_PINNED_PUBLIC_ORIGIN}/robots.txt").mock(
        return_value=httpx.Response(
            302, headers={"Location": destination}
        )
    )
    unsafe_robots = respx_mock.get(destination).mock(
        return_value=httpx.Response(
            200, text="User-agent: *\nAllow: /"
        )
    )
    resource = respx_mock.get(f"{_PINNED_PUBLIC_ORIGIN}/person").mock(
        return_value=httpx.Response(200, text="<title>unsafe</title>")
    )
    crawler = HttpCrawler(settings, SqliteCache(tmp_path / "cache.sqlite3"))

    result = await PublicWebSource(crawler).enrich_urls(
        ("https://safe.example/person",)
    )

    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert unsafe_robots.call_count == 0
    assert resource.call_count == 0


@pytest.mark.asyncio
async def test_public_homepage_blocks_dns_private_robots_redirect(
    tmp_path, respx_mock, settings, monkeypatch
):
    def dns(host, port, *args, **kwargs):
        if host == "private.example":
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    socket.IPPROTO_TCP,
                    "",
                    ("10.0.0.8", port),
                )
            ]
        return _public_dns(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", dns)
    respx_mock.get(f"{_PINNED_PUBLIC_ORIGIN}/robots.txt").mock(
        return_value=httpx.Response(
            302,
            headers={
                "Location": "https://private.example/robots.txt"
            },
        )
    )
    unsafe_robots = respx_mock.get(
        "https://private.example/robots.txt"
    ).mock(return_value=httpx.Response(200, text="User-agent: *\nAllow: /"))
    resource = respx_mock.get(f"{_PINNED_PUBLIC_ORIGIN}/person").mock(
        return_value=httpx.Response(200, text="<title>unsafe</title>")
    )
    crawler = HttpCrawler(settings, SqliteCache(tmp_path / "cache.sqlite3"))

    result = await PublicWebSource(crawler).enrich_urls(
        ("https://safe.example/person",)
    )

    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert unsafe_robots.call_count == 0
    assert resource.call_count == 0


@pytest.mark.asyncio
async def test_public_homepage_pins_redirected_robots_host(
    tmp_path, settings, monkeypatch
):
    resolution_calls = []
    addresses = {
        "safe.example": "93.184.216.34",
        "robots.example": "1.1.1.1",
    }

    def dns(host, port, *args, **kwargs):
        resolution_calls.append((host, port))
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (addresses[host], port),
            )
        ]

    requests = []

    def handler(request):
        requests.append(request)
        if request.url.host == "93.184.216.34":
            return httpx.Response(
                302,
                headers={
                    "Location": "https://robots.example/rules.txt"
                },
                request=request,
            )
        return httpx.Response(
            200,
            text="User-agent: *\nDisallow: /person",
            request=request,
        )

    def direct_client(_crawler, *, direct=False):
        assert direct is True
        return httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=False,
            trust_env=False,
        )

    monkeypatch.setattr(socket, "getaddrinfo", dns)
    monkeypatch.setattr(HttpCrawler, "_client", direct_client)
    crawler = HttpCrawler(settings, SqliteCache(tmp_path / "cache.sqlite3"))

    result = await PublicWebSource(crawler).enrich_urls(
        ("https://safe.example/person",)
    )

    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert resolution_calls == [
        ("safe.example", 443),
        ("robots.example", 443),
    ]
    assert [request.url.host for request in requests] == [
        "93.184.216.34",
        "1.1.1.1",
    ]
    assert [request.headers["Host"] for request in requests] == [
        "safe.example",
        "robots.example",
    ]
    assert [request.extensions["sni_hostname"] for request in requests] == [
        "safe.example",
        "robots.example",
    ]
