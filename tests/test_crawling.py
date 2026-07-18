import httpx
import pytest

from researcher_recruiting.cache import SqliteCache
from researcher_recruiting.crawling import HttpCrawler
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
