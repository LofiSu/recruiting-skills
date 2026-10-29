"""Small urllib JSON client with pacing and 429 retries.

No third-party HTTP library. Callers inject a transport in tests so the suite
never opens a socket.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import Callable, Optional, Sequence


USER_AGENT = (
    "recruiting-skills-connectors/1.0 "
    "(https://github.com/LofiSu/recruiting-skills; public metadata only)"
)
_API_KEY_QUERY = re.compile(r"(api_key=)[^&\s]+", re.IGNORECASE)
_BEARER = re.compile(r"(Bearer\s+)\S+", re.IGNORECASE)


class ConnectorError(Exception):
    """A public-API call failed or returned a document we cannot use."""


class Response:
    def __init__(self, status: int, body: bytes, headers: Optional[dict] = None):
        self.status = status
        self.body = body
        self.headers = {str(key).lower(): value for key, value in (headers or {}).items()}


class UrllibTransport:
    """Real HTTP transport. Tests must not construct this."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def request(self, url: str, headers: dict) -> Response:
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return Response(response.status, response.read(), dict(response.headers))
        except urllib.error.HTTPError as error:
            return Response(error.code, error.read(), dict(error.headers or {}))
        except urllib.error.URLError as error:
            raise ConnectorError(f"request failed for {_redact(url)}: {error.reason}") from error


class JsonClient:
    def __init__(
        self,
        transport,
        *,
        delay: float = 1.0,
        max_retries: int = 3,
        user_agent: str = USER_AGENT,
        default_headers: Optional[dict] = None,
        secrets: Sequence[str] = (),
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        if delay < 0:
            raise ValueError("delay must be >= 0")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self.transport = transport
        self.delay = delay
        self.max_retries = max_retries
        self.user_agent = user_agent
        self.default_headers = dict(default_headers or {})
        self.secrets = tuple(secret for secret in secrets if secret)
        self._sleeper = sleeper
        self._clock = clock
        self._now = now
        self._next_allowed = 0.0

    def get_json(self, url: str, headers: Optional[dict] = None) -> dict:
        merged = {"User-Agent": self.user_agent, "Accept": "application/json"}
        merged.update(self.default_headers)
        if headers:
            merged.update(headers)
        last_error = "request failed"
        for attempt in range(self.max_retries + 1):
            self._pace()
            response = self.transport.request(url, merged)
            if response.status in (429, 503):
                last_error = f"HTTP {response.status} from {_redact(url, self.secrets)}"
                if attempt == self.max_retries:
                    break
                self._sleeper(_retry_delay(response.headers.get("retry-after", ""), attempt, self._now()))
                continue
            if response.status != 200:
                body = _decode(response.body)
                raise ConnectorError(
                    f"HTTP {response.status} from {_redact(url, self.secrets)}: "
                    f"{_redact(body[:300], self.secrets)}"
                )
            try:
                payload = json.loads(response.body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ConnectorError(f"invalid JSON from {_redact(url, self.secrets)}") from error
            if not isinstance(payload, dict):
                raise ConnectorError(f"expected a JSON object from {_redact(url, self.secrets)}")
            return payload
        raise ConnectorError(
            f"{last_error} after {self.max_retries} retries. "
            "Wait and retry later, or lower the request rate."
        )

    def _pace(self) -> None:
        now = self._clock()
        if now < self._next_allowed:
            self._sleeper(self._next_allowed - now)
        self._next_allowed = self._clock() + self.delay


def _decode(body: bytes) -> str:
    try:
        return body.decode("utf-8", errors="replace")
    except AttributeError:
        return ""


def _redact(text: str, secrets: Sequence[str] = ()) -> str:
    cleaned = _BEARER.sub(r"\1REDACTED", _API_KEY_QUERY.sub(r"\1REDACTED", text))
    for secret in secrets:
        cleaned = cleaned.replace(secret, "REDACTED")
    return cleaned


def _retry_delay(value: str, attempt: int, now: datetime) -> float:
    fallback = float(min(2 ** attempt, 30))
    if not value:
        return fallback
    try:
        return min(max(float(value), 0.0), 60.0)
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return fallback
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return min(max((when - now).total_seconds(), 0.0), 60.0)
