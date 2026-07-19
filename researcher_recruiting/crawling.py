import asyncio
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Awaitable, Callable, Mapping
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from researcher_recruiting.cache import SqliteCache, cache_key
from researcher_recruiting.config import Settings
from researcher_recruiting.models import SourceStatus


class _ResponseTooLarge(Exception):
    pass


class _UnsupportedContentType(Exception):
    pass


URLSafetyPolicy = Callable[[str], Awaitable[bool]]


@dataclass(frozen=True)
class FetchPolicy:
    max_attempts: int = 3
    max_redirects: int = 5
    base_delay_seconds: float = 0.25
    per_domain_delay_seconds: float = 0.5
    max_retry_after_seconds: float = 30.0
    allowed_content_types: tuple[str, ...] = (
        "text/html",
        "text/plain",
        "application/json",
        "application/atom+xml",
        "application/xml",
        "text/xml",
    )


@dataclass(frozen=True)
class FetchResult:
    status: SourceStatus
    url: str
    status_code: int | None
    content_type: str | None
    body: bytes
    from_cache: bool
    error: str | None = None


class HttpCrawler:
    REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        settings: Settings,
        cache: SqliteCache,
        policy: FetchPolicy | None = None,
    ) -> None:
        self.settings = settings
        self.cache = cache
        self.policy = policy or FetchPolicy()
        self._domain_locks: dict[str, asyncio.Lock] = {}
        self._last_request_at: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser] = {}
        self.force_refresh = False

    def _client(self) -> httpx.AsyncClient:
        proxy = self.settings.https_proxy or self.settings.http_proxy
        return httpx.AsyncClient(
            headers={"User-Agent": self.settings.user_agent},
            follow_redirects=False,
            timeout=self.settings.request_timeout_seconds,
            proxy=proxy,
        )

    async def _throttle(self, host: str) -> None:
        elapsed = time.monotonic() - self._last_request_at.get(host, 0)
        delay = self.policy.per_domain_delay_seconds - elapsed
        if delay > 0:
            await asyncio.sleep(delay)
        self._last_request_at[host] = time.monotonic()

    async def _robots_allows(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            robots_url = f"{origin}/robots.txt"
            parser = RobotFileParser()
            parser.set_url(robots_url)
            try:
                async with self._client() as client:
                    response = await client.get(robots_url)
                if response.status_code < 400:
                    parser.parse(response.text.splitlines())
                else:
                    parser.parse([])
            except httpx.HTTPError:
                parser.parse([])
            self._robots[origin] = parser
        return self._robots[origin].can_fetch(self.settings.user_agent, url)

    @staticmethod
    def _content_type(response: httpx.Response) -> str | None:
        value = response.headers.get("Content-Type")
        return value.split(";", 1)[0].strip().lower() if value else None

    def _content_type_allowed(self, content_type: str | None) -> bool:
        return (
            content_type is None
            or content_type in self.policy.allowed_content_types
            or content_type.endswith("+json")
            or content_type.endswith("+xml")
        )

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                try:
                    timestamp = parsedate_to_datetime(retry_after).timestamp()
                    return max(0.0, timestamp - time.time())
                except (TypeError, ValueError, OverflowError):
                    pass
        return self.policy.base_delay_seconds * (2**attempt)

    async def _request(
        self,
        url: str,
        headers: Mapping[str, str],
    ) -> httpx.Response:
        host = urlsplit(url).netloc
        lock = self._domain_locks.setdefault(host, asyncio.Lock())
        last_error: httpx.HTTPError | None = None
        for attempt in range(self.policy.max_attempts):
            async with lock:
                await self._throttle(host)
                try:
                    async with self._client() as client:
                        async with client.stream(
                            "GET", url, headers=headers
                        ) as streamed:
                            if (
                                streamed.status_code
                                in self.REDIRECT_STATUS_CODES
                            ):
                                chunks = []
                            else:
                                content_type = self._content_type(streamed)
                                if not self._content_type_allowed(content_type):
                                    raise _UnsupportedContentType(content_type)
                                content_length = streamed.headers.get(
                                    "Content-Length"
                                )
                                if (
                                    content_length
                                    and int(content_length)
                                    > self.settings.max_response_bytes
                                ):
                                    raise _ResponseTooLarge
                                chunks = []
                                size = 0
                                async for chunk in streamed.aiter_bytes():
                                    size += len(chunk)
                                    if size > self.settings.max_response_bytes:
                                        raise _ResponseTooLarge
                                    chunks.append(chunk)
                            response = httpx.Response(
                                streamed.status_code,
                                headers=streamed.headers,
                                content=b"".join(chunks),
                                request=streamed.request,
                            )
                except httpx.HTTPError as error:
                    last_error = error
                    response = None
            if response is not None:
                if response.status_code not in self.RETRYABLE_STATUS_CODES:
                    return response
                if attempt + 1 == self.policy.max_attempts:
                    return response
                retry_delay = self._retry_delay(response, attempt)
                if retry_delay > self.policy.max_retry_after_seconds:
                    return response
                await asyncio.sleep(retry_delay)
            elif attempt + 1 < self.policy.max_attempts:
                await asyncio.sleep(self.policy.base_delay_seconds * (2**attempt))
        assert last_error is not None
        raise last_error

    @staticmethod
    def _http_url(url: str) -> bool:
        try:
            parts = urlsplit(url)
            hostname = parts.hostname
        except ValueError:
            return False
        return parts.scheme.casefold() in {"http", "https"} and bool(
            hostname
        )

    async def _url_allowed(
        self,
        url: str,
        url_safety: URLSafetyPolicy | None,
    ) -> bool:
        if not self._http_url(url):
            return False
        return url_safety is None or await url_safety(url)

    async def fetch(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        refresh: bool = False,
        url_safety: URLSafetyPolicy | None = None,
    ) -> FetchResult:
        target = str(httpx.URL(url, params=params))
        request_headers = dict(headers or {})
        key = cache_key("GET", target, request_headers)
        if not await self._url_allowed(target, url_safety):
            return FetchResult(
                SourceStatus.SOURCE_UNAVAILABLE,
                target,
                None,
                None,
                b"",
                False,
                "url_not_allowed",
            )
        if not (refresh or self.force_refresh):
            cached = self.cache.get(key)
            if cached and await self._url_allowed(cached.url, url_safety):
                return FetchResult(
                    status=SourceStatus.OK,
                    url=cached.url,
                    status_code=cached.status_code,
                    content_type=cached.content_type,
                    body=cached.body,
                    from_cache=True,
                )

        current = target
        redirects = 0
        while True:
            if not await self._url_allowed(current, url_safety):
                return FetchResult(
                    SourceStatus.SOURCE_UNAVAILABLE,
                    current,
                    None,
                    None,
                    b"",
                    False,
                    "url_not_allowed",
                )
            if not await self._robots_allows(current):
                return FetchResult(
                    status=SourceStatus.BLOCKED_BY_ROBOTS,
                    url=current,
                    status_code=None,
                    content_type=None,
                    body=b"",
                    from_cache=False,
                    error="blocked_by_robots",
                )

            try:
                response = await self._request(current, request_headers)
            except _UnsupportedContentType as error:
                return FetchResult(
                    SourceStatus.SOURCE_UNAVAILABLE,
                    current,
                    None,
                    str(error),
                    b"",
                    False,
                    "unsupported_content_type",
                )
            except _ResponseTooLarge:
                return FetchResult(
                    SourceStatus.SOURCE_UNAVAILABLE,
                    current,
                    None,
                    None,
                    b"",
                    False,
                    "response_too_large",
                )
            except httpx.HTTPError as error:
                return FetchResult(
                    status=SourceStatus.SOURCE_UNAVAILABLE,
                    url=current,
                    status_code=None,
                    content_type=None,
                    body=b"",
                    from_cache=False,
                    error=type(error).__name__,
                )

            location = response.headers.get("Location")
            if (
                response.status_code in self.REDIRECT_STATUS_CODES
                and location
            ):
                if redirects >= self.policy.max_redirects:
                    return FetchResult(
                        SourceStatus.SOURCE_UNAVAILABLE,
                        current,
                        response.status_code,
                        None,
                        b"",
                        False,
                        "too_many_redirects",
                    )
                try:
                    current = str(httpx.URL(urljoin(current, location)))
                except (httpx.InvalidURL, ValueError):
                    return FetchResult(
                        SourceStatus.SOURCE_UNAVAILABLE,
                        current,
                        response.status_code,
                        None,
                        b"",
                        False,
                        "invalid_redirect",
                    )
                redirects += 1
                continue
            break

        content_type = self._content_type(response)
        if not self._content_type_allowed(content_type):
            return FetchResult(
                SourceStatus.SOURCE_UNAVAILABLE,
                current,
                response.status_code,
                content_type,
                b"",
                False,
                "unsupported_content_type",
            )
        if len(response.content) > self.settings.max_response_bytes:
            return FetchResult(
                SourceStatus.SOURCE_UNAVAILABLE,
                current,
                response.status_code,
                content_type,
                b"",
                False,
                "response_too_large",
            )
        if response.status_code == 404:
            status = SourceStatus.NOT_FOUND
        elif response.is_success:
            status = SourceStatus.OK
        else:
            status = SourceStatus.SOURCE_UNAVAILABLE
        if status is SourceStatus.OK:
            self.cache.put(key, response)
        return FetchResult(
            status=status,
            url=current,
            status_code=response.status_code,
            content_type=content_type,
            body=response.content,
            from_cache=False,
            error=None if status is SourceStatus.OK else f"http_{response.status_code}",
        )
