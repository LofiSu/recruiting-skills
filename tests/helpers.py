from dataclasses import dataclass
from typing import Mapping

from researcher_recruiting.crawling import FetchResult
from researcher_recruiting.models import SourceStatus


@dataclass(frozen=True)
class RecordedRequest:
    url: str
    params: Mapping[str, str]
    headers: Mapping[str, str]


class StubCrawler:
    def __init__(self, responses: Mapping[str, list[FetchResult]]) -> None:
        self.responses = {key: list(value) for key, value in responses.items()}
        self.requests: list[RecordedRequest] = []

    @property
    def last_params(self) -> Mapping[str, str]:
        return self.requests[-1].params

    async def fetch(self, url, *, params=None, headers=None, refresh=False):
        self.requests.append(
            RecordedRequest(url, dict(params or {}), dict(headers or {}))
        )
        return self.responses[url].pop(0)


def fixture_crawler(
    url: str,
    json_text: str,
    content_type: str = "application/json",
) -> StubCrawler:
    return StubCrawler(
        {
            url: [
                FetchResult(
                    SourceStatus.OK,
                    url,
                    200,
                    content_type,
                    json_text.encode(),
                    False,
                )
            ]
        }
    )


def sequential_fixture_crawler(
    responses: Mapping[str, str],
) -> StubCrawler:
    return StubCrawler(
        {
            url: [
                FetchResult(
                    SourceStatus.OK,
                    url,
                    200,
                    "application/json",
                    body.encode(),
                    False,
                )
            ]
            for url, body in responses.items()
        }
    )
