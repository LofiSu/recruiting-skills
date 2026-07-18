import httpx

from researcher_recruiting.cache import SqliteCache, cache_key


def test_cache_key_redacts_secret_query_values():
    key = cache_key(
        "GET",
        "https://example.test/profile?token=secret&name=Ada",
        {"Authorization": "Bearer secret"},
    )
    assert "secret" not in key
    assert "name=Ada" in key


def test_cache_round_trip_stores_public_response_only(tmp_path):
    cache = SqliteCache(tmp_path / "cache.sqlite3")
    response = httpx.Response(
        200,
        content=b'{"name":"Ada"}',
        headers={"Content-Type": "application/json", "Set-Cookie": "secret=1"},
        request=httpx.Request("GET", "https://example.test/person"),
    )
    cache.put("public-key", response)
    cached = cache.get("public-key")
    assert cached is not None
    assert cached.url == "https://example.test/person"
    assert cached.body == b'{"name":"Ada"}'
    assert not hasattr(cached, "headers")
