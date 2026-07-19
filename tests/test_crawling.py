import httpx
import pytest

from researcher_recruiting.cache import SqliteCache
from researcher_recruiting.crawling import FetchPolicy, HttpCrawler
from researcher_recruiting.models import SourceStatus


def allow_robots(respx_mock):
    return respx_mock.get("https://example.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /")
    )


@pytest.mark.asyncio
async def test_crawler_refuses_robots_denied_url(tmp_path, respx_mock, settings):
    respx_mock.get("https://example.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /private")
    )
    crawler = HttpCrawler(settings, SqliteCache(tmp_path / "cache.sqlite3"))
    result = await crawler.fetch("https://example.test/private/person")
    assert result.status is SourceStatus.BLOCKED_BY_ROBOTS


@pytest.mark.asyncio
async def test_crawler_honors_retry_after_then_succeeds(
    tmp_path, respx_mock, settings
):
    allow_robots(respx_mock)
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


@pytest.mark.asyncio
async def test_crawler_does_not_retry_beyond_retry_after_budget(
    tmp_path, respx_mock, settings, monkeypatch
):
    async def no_sleep(_delay):
        return None

    monkeypatch.setattr(
        "researcher_recruiting.crawling.asyncio.sleep", no_sleep
    )
    allow_robots(respx_mock)
    route = respx_mock.get("https://example.test/person").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "600"}),
            httpx.Response(200, text="should-not-be-requested"),
        ]
    )
    result = await HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    ).fetch("https://example.test/person")
    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_crawler_rejects_unsupported_content_type(
    tmp_path, respx_mock, settings
):
    allow_robots(respx_mock)
    respx_mock.get("https://example.test/person").mock(
        return_value=httpx.Response(
            200, content=b"%PDF", headers={"Content-Type": "application/pdf"}
        )
    )
    result = await HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    ).fetch("https://example.test/person")
    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert result.error == "unsupported_content_type"


@pytest.mark.asyncio
async def test_crawler_accepts_registered_vendor_json(
    tmp_path, respx_mock, settings
):
    allow_robots(respx_mock)
    respx_mock.get("https://example.test/person").mock(
        return_value=httpx.Response(
            200,
            content=b'{"name":"Ada"}',
            headers={"Content-Type": "application/vnd.orcid+json"},
        )
    )
    result = await HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    ).fetch("https://example.test/person")
    assert result.status is SourceStatus.OK


@pytest.mark.asyncio
async def test_crawler_rejects_oversized_body(tmp_path, respx_mock, settings):
    allow_robots(respx_mock)
    respx_mock.get("https://example.test/person").mock(
        return_value=httpx.Response(200, content=b"x" * 65)
    )
    result = await HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    ).fetch("https://example.test/person")
    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert result.error == "response_too_large"


@pytest.mark.asyncio
async def test_crawler_uses_cache_unless_refresh_requested(
    tmp_path, respx_mock, settings
):
    allow_robots(respx_mock)
    route = respx_mock.get("https://example.test/person").mock(
        side_effect=[
            httpx.Response(200, text="first"),
            httpx.Response(200, text="second"),
        ]
    )
    crawler = HttpCrawler(settings, SqliteCache(tmp_path / "cache.sqlite3"))
    first = await crawler.fetch("https://example.test/person")
    cached = await crawler.fetch("https://example.test/person")
    refreshed = await crawler.fetch(
        "https://example.test/person", refresh=True
    )
    assert first.body == cached.body == b"first"
    assert cached.from_cache is True
    assert refreshed.body == b"second"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_crawler_force_refresh_bypasses_cache(
    tmp_path, respx_mock, settings
):
    allow_robots(respx_mock)
    route = respx_mock.get("https://example.test/person").mock(
        side_effect=[
            httpx.Response(200, text="first"),
            httpx.Response(200, text="second"),
        ]
    )
    crawler = HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    )
    first = await crawler.fetch("https://example.test/person")
    crawler.force_refresh = True
    second = await crawler.fetch("https://example.test/person")
    assert first.body == b"first"
    assert second.body == b"second"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_crawler_checks_robots_for_each_redirect_hop(
    tmp_path, respx_mock, settings
):
    allow_robots(respx_mock)
    respx_mock.get("https://example.test/person").mock(
        return_value=httpx.Response(
            302, headers={"Location": "https://other.test/private"}
        )
    )
    respx_mock.get("https://other.test/robots.txt").mock(
        return_value=httpx.Response(
            200, text="User-agent: *\nDisallow: /private"
        )
    )
    blocked = respx_mock.get("https://other.test/private").mock(
        return_value=httpx.Response(200, text="must not be requested")
    )

    result = await HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    ).fetch("https://example.test/person")

    assert result.status is SourceStatus.BLOCKED_BY_ROBOTS
    assert result.url == "https://other.test/private"
    assert blocked.call_count == 0


@pytest.mark.asyncio
async def test_crawler_reports_final_redirect_url(
    tmp_path, respx_mock, settings
):
    allow_robots(respx_mock)
    respx_mock.get("https://other.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /")
    )
    respx_mock.get("https://example.test/person").mock(
        return_value=httpx.Response(
            302, headers={"Location": "https://other.test/final"}
        )
    )
    respx_mock.get("https://other.test/final").mock(
        return_value=httpx.Response(200, text="final")
    )

    result = await HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    ).fetch("https://example.test/person")

    assert result.status is SourceStatus.OK
    assert result.url == "https://other.test/final"
    assert result.body == b"final"


@pytest.mark.asyncio
async def test_crawler_bounds_redirect_hops(tmp_path, respx_mock, settings):
    allow_robots(respx_mock)
    route = respx_mock.get("https://example.test/robots.txt")
    for index in range(6):
        respx_mock.get(f"https://example.test/{index}").mock(
            return_value=httpx.Response(
                302, headers={"Location": f"/{index + 1}"}
            )
        )
    final = respx_mock.get("https://example.test/6").mock(
        return_value=httpx.Response(200, text="must not be requested")
    )

    result = await HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    ).fetch("https://example.test/0")

    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert result.error == "too_many_redirects"
    assert route.call_count == 1
    assert final.call_count == 0


@pytest.mark.asyncio
async def test_crawler_handles_malformed_redirect_without_details(
    tmp_path, respx_mock, settings
):
    allow_robots(respx_mock)
    respx_mock.get("https://example.test/person").mock(
        return_value=httpx.Response(
            302, headers={"Location": "http://[malformed"}
        )
    )

    result = await HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    ).fetch("https://example.test/person")

    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert result.error == "invalid_redirect"


@pytest.mark.asyncio
async def test_crawler_strips_credentials_on_cross_origin_redirect(
    tmp_path, respx_mock, settings
):
    allow_robots(respx_mock)
    respx_mock.get("https://other.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /")
    )
    respx_mock.get("https://example.test/person").mock(
        return_value=httpx.Response(
            302, headers={"Location": "https://other.test/final"}
        )
    )
    final = respx_mock.get("https://other.test/final").mock(
        return_value=httpx.Response(200, text="final")
    )

    result = await HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    ).fetch(
        "https://example.test/person",
        headers={
            "aUtHoRiZaTiOn": "Bearer secret",
            "COOKIE": "session=secret",
            "pRoXy-AuThOrIzAtIoN": "Basic secret",
            "X-aPi-KeY": "secret-api-key",
        },
    )

    assert result.status is SourceStatus.OK
    assert "Authorization" not in final.calls[0].request.headers
    assert "Cookie" not in final.calls[0].request.headers
    assert "Proxy-Authorization" not in final.calls[0].request.headers
    assert "X-API-Key" not in final.calls[0].request.headers


@pytest.mark.asyncio
async def test_crawler_retains_credentials_on_same_origin_redirect(
    tmp_path, respx_mock, settings
):
    allow_robots(respx_mock)
    respx_mock.get("https://example.test/person").mock(
        return_value=httpx.Response(302, headers={"Location": "/final"})
    )
    final = respx_mock.get("https://example.test/final").mock(
        return_value=httpx.Response(200, text="final")
    )

    result = await HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    ).fetch(
        "https://example.test/person",
        headers={
            "Authorization": "Bearer secret",
            "Cookie": "session=secret",
            "Proxy-Authorization": "Basic secret",
        },
    )

    assert result.status is SourceStatus.OK
    assert final.calls[0].request.headers["Authorization"] == "Bearer secret"
    assert final.calls[0].request.headers["Cookie"] == "session=secret"
    assert (
        final.calls[0].request.headers["Proxy-Authorization"]
        == "Basic secret"
    )


@pytest.mark.asyncio
async def test_crawler_follows_robots_redirect_and_honors_disallow(
    tmp_path, respx_mock, settings
):
    respx_mock.get("https://example.test/robots.txt").mock(
        return_value=httpx.Response(
            302, headers={"Location": "/robots-final.txt"}
        )
    )
    respx_mock.get("https://example.test/robots-final.txt").mock(
        return_value=httpx.Response(
            200, text="User-agent: *\nDisallow: /private"
        )
    )
    resource = respx_mock.get("https://example.test/private/person").mock(
        return_value=httpx.Response(200, text="must not be requested")
    )

    result = await HttpCrawler(
        settings, SqliteCache(tmp_path / "cache.sqlite3")
    ).fetch("https://example.test/private/person")

    assert result.status is SourceStatus.BLOCKED_BY_ROBOTS
    assert resource.call_count == 0


@pytest.mark.asyncio
async def test_robots_and_resource_redirects_share_one_budget(
    tmp_path, respx_mock, settings
):
    respx_mock.get("https://example.test/robots.txt").mock(
        return_value=httpx.Response(
            302, headers={"Location": "/robots-final.txt"}
        )
    )
    respx_mock.get("https://example.test/robots-final.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /")
    )
    respx_mock.get("https://example.test/person").mock(
        return_value=httpx.Response(302, headers={"Location": "/final"})
    )
    final = respx_mock.get("https://example.test/final").mock(
        return_value=httpx.Response(200, text="must not be requested")
    )
    crawler = HttpCrawler(
        settings,
        SqliteCache(tmp_path / "cache.sqlite3"),
        FetchPolicy(max_redirects=1, per_domain_delay_seconds=0),
    )

    result = await crawler.fetch("https://example.test/person")

    assert result.status is SourceStatus.SOURCE_UNAVAILABLE
    assert result.error == "too_many_redirects"
    assert final.call_count == 0


@pytest.mark.asyncio
async def test_crawler_blocks_robots_redirect_loop_at_limit(
    tmp_path, respx_mock, settings
):
    respx_mock.get("https://example.test/robots.txt").mock(
        return_value=httpx.Response(
            302, headers={"Location": "/robots-again.txt"}
        )
    )
    respx_mock.get("https://example.test/robots-again.txt").mock(
        return_value=httpx.Response(
            302, headers={"Location": "/robots.txt"}
        )
    )
    resource = respx_mock.get("https://example.test/person").mock(
        return_value=httpx.Response(200, text="must not be requested")
    )
    crawler = HttpCrawler(
        settings,
        SqliteCache(tmp_path / "cache.sqlite3"),
        FetchPolicy(max_redirects=1, per_domain_delay_seconds=0),
    )

    result = await crawler.fetch("https://example.test/person")

    assert result.status is SourceStatus.BLOCKED_BY_ROBOTS
    assert resource.call_count == 0
