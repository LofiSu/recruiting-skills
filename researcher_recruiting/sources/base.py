import json
from datetime import datetime, timezone
from typing import Any, Protocol

from researcher_recruiting.models import AuthorSeed, Evidence, SourceResult


class SourceClient(Protocol):
    name: str

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        ...


def collected_at() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def decode_json(body: bytes) -> Any:
    return json.loads(body.decode("utf-8"))


def evidence(
    *,
    source: str,
    field: str,
    value: object,
    url: str,
    candidate_id: str | None,
    metadata: dict[str, object] | None = None,
) -> Evidence:
    return Evidence(
        source=source,
        field=field,
        value=str(value),
        url=url,
        collected_at=collected_at(),
        candidate_id=candidate_id,
        metadata=metadata or {},
    )


def content_value(content: dict[str, Any], key: str) -> Any:
    value = content.get(key)
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value
