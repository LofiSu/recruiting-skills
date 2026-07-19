import ipaddress
import re
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from researcher_recruiting.models import SourceResult, SourceStatus
from researcher_recruiting.sources.base import evidence

_RESTRICTED_HOSTS = (
    "academia.edu",
    "dimensions.ai",
    "ieeexplore.ieee.org",
    "lens.org",
    "link.springer.com",
    "linkedin.com",
    "maimai.cn",
    "researchgate.net",
    "scholar.google.",
    "scopus.com",
    "ui.adsabs.harvard.edu",
    "webofscience.com",
)
_EMAIL_PATTERN = re.compile(
    r"[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+",
    re.IGNORECASE,
)


def _host_matches(host: str, blocked: str) -> bool:
    if blocked.endswith("."):
        return host.startswith(blocked) or f".{blocked}" in host
    return host == blocked or host.endswith(f".{blocked}")


def _is_restricted_host(host: str) -> bool:
    normalized = host.casefold().rstrip(".")
    return any(
        _host_matches(normalized, restricted)
        for restricted in _RESTRICTED_HOSTS
    )


def _is_safe_public_url(url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return False
    host = parts.hostname.casefold().rstrip(".")
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
    )


def _same_origin(left: str, right: str) -> bool:
    left_parts = urlsplit(left)
    right_parts = urlsplit(right)
    return (
        left_parts.scheme.casefold(),
        left_parts.netloc.casefold(),
    ) == (
        right_parts.scheme.casefold(),
        right_parts.netloc.casefold(),
    )


def _public_email(href: str) -> str | None:
    value = unquote(href.split(":", 1)[1].split("?", 1)[0]).strip()
    return value.casefold() if _EMAIL_PATTERN.fullmatch(value) else None


class PublicWebSource:
    name = "public_web"

    def __init__(self, crawler: Any) -> None:
        self.crawler = crawler

    def _extract(
        self,
        page_url: str,
        body: bytes,
        candidate_id: str,
    ) -> tuple[list, list[str]]:
        soup = BeautifulSoup(body, "html.parser")
        items = []
        follow_candidates = []
        canonical_tag = soup.find("link", rel=lambda value: value and "canonical" in value)
        canonical = (
            urljoin(page_url, canonical_tag.get("href"))
            if canonical_tag and canonical_tag.get("href")
            else page_url
        )
        items.append(
            evidence(
                source=self.name,
                field="homepage",
                value=canonical,
                url=page_url,
                candidate_id=candidate_id,
            )
        )
        if soup.title and soup.title.string:
            items.append(
                evidence(
                    source=self.name,
                    field="page_title",
                    value=" ".join(soup.title.string.split()),
                    url=page_url,
                    candidate_id=candidate_id,
                )
            )
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "").strip()
            if href.casefold().startswith("mailto:"):
                email = _public_email(href)
                if email:
                    items.append(
                        evidence(
                            source=self.name,
                            field="email",
                            value=email,
                            url=page_url,
                            candidate_id=candidate_id,
                            metadata={
                                "visibility": "public_professional"
                            },
                        )
                    )
                continue
            linked_url = urljoin(page_url, href)
            if not _is_safe_public_url(linked_url):
                continue
            linked = urlsplit(linked_url)
            host = (linked.hostname or "").casefold()
            if _is_restricted_host(host):
                continue
            path = linked.path.casefold()
            anchor_text = " ".join(
                anchor.get_text(" ", strip=True).split()
            ).casefold()
            field = None
            value = linked_url
            if _host_matches(host, "github.com"):
                field = "github"
                value = path.strip("/").split("/", 1)[0] or linked_url
            elif _host_matches(host, "orcid.org"):
                field = "orcid"
                value = path.strip("/").split("/", 1)[0] or linked_url
            elif _host_matches(host, "openreview.net"):
                field = "openreview"
            elif _host_matches(host, "semanticscholar.org"):
                field = "semantic_scholar"
            elif _same_origin(page_url, linked_url) and (
                "contact" in path or "contact" in anchor_text
            ):
                field = "contact_form"
            elif _same_origin(page_url, linked_url) and (
                "lab" in path or "group" in path
            ):
                field = "lab"
                follow_candidates.append(linked_url)
            elif _same_origin(page_url, linked_url) and (
                "cv" in path or "vita" in path
            ):
                field = "cv"
                follow_candidates.append(linked_url)
            if field:
                items.append(
                    evidence(
                        source=self.name,
                        field=field,
                        value=value,
                        url=page_url,
                        candidate_id=candidate_id,
                    )
                )
        return items, follow_candidates

    async def enrich_urls(self, urls: tuple[str, ...]) -> SourceResult:
        safe_urls = tuple(
            dict.fromkeys(
                url
                for url in urls
                if _is_safe_public_url(url)
                and not _is_restricted_host(
                    urlsplit(url).hostname or ""
                )
            )
        )
        if not safe_urls:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)
        items = []
        unavailable = False
        for url in safe_urls:
            response = await self.crawler.fetch(url)
            if response.status is not SourceStatus.OK:
                unavailable = True
                continue
            candidate_id = f"public_web:{url}"
            page_items, follow_candidates = self._extract(
                response.url or url, response.body, candidate_id
            )
            items.extend(page_items)
            if follow_candidates:
                follow_url = next(
                    (
                        candidate
                        for candidate in follow_candidates
                        if _same_origin(url, candidate)
                    ),
                    None,
                )
                if follow_url:
                    follow_response = await self.crawler.fetch(follow_url)
                    if follow_response.status is SourceStatus.OK:
                        follow_items, _ = self._extract(
                            follow_url,
                            follow_response.body,
                            candidate_id,
                        )
                        items.extend(follow_items)
        if items:
            return SourceResult(self.name, SourceStatus.OK, tuple(items))
        if unavailable:
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="public_homepages_unavailable",
            )
        return SourceResult(self.name, SourceStatus.NOT_FOUND)
