from researcher_recruiting.config import Settings


def test_settings_read_optional_tokens_and_proxy(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_TOKEN", "github-secret")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:7890")
    monkeypatch.setenv(
        "RESEARCHER_RECRUITING_CACHE", str(tmp_path / "cache.sqlite3")
    )
    settings = Settings.from_env()
    assert settings.github_token == "github-secret"
    assert settings.https_proxy == "http://127.0.0.1:7890"
    assert settings.cache_path == tmp_path / "cache.sqlite3"
