import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

_SECRET_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "client_secret",
    "key",
    "token",
}
_SECRET_HEADER_KEYS = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "x-api-key",
}


def _sanitize_url(url: str) -> str:
    parts = urlsplit(url)
    query = [
        (key, "<redacted>" if key.lower() in _SECRET_QUERY_KEYS else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(sorted(query)), "")
    )


def cache_key(method: str, url: str, headers: Mapping[str, str] | None = None) -> str:
    safe_headers = [
        (
            key.lower(),
            "<redacted>" if key.lower() in _SECRET_HEADER_KEYS else value,
        )
        for key, value in (headers or {}).items()
    ]
    serialized_headers = "&".join(
        f"{key}={value}" for key, value in sorted(safe_headers)
    )
    return f"{method.upper()} {_sanitize_url(url)} {serialized_headers}".rstrip()


@dataclass(frozen=True)
class CachedResponse:
    url: str
    status_code: int
    content_type: str | None
    body: bytes
    fetched_at: str


class SqliteCache:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS responses (
                  cache_key TEXT PRIMARY KEY,
                  url TEXT NOT NULL,
                  status_code INTEGER NOT NULL,
                  content_type TEXT,
                  body BLOB NOT NULL,
                  fetched_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def get(self, key: str) -> CachedResponse | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT url, status_code, content_type, body, fetched_at
                FROM responses WHERE cache_key = ?
                """,
                (key,),
            ).fetchone()
        return CachedResponse(*row) if row else None

    def put(self, key: str, response: httpx.Response) -> None:
        content_type = response.headers.get("Content-Type")
        if content_type:
            content_type = content_type.split(";", 1)[0].strip().lower()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO responses
                (cache_key, url, status_code, content_type, body, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    _sanitize_url(str(response.request.url)),
                    response.status_code,
                    content_type,
                    response.content,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
