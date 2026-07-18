from typing import Any

from researcher_recruiting.models import AuthorSeed, SourceResult, SourceStatus
from researcher_recruiting.sources.base import decode_json, evidence

PUBMED_SEARCH = (
    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
)
PUBMED_SUMMARY = (
    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
)


class PubmedSource:
    name = "pubmed"

    def __init__(self, crawler: Any, api_key: str | None) -> None:
        self.crawler = crawler
        self.api_key = api_key

    async def enrich(self, seed: AuthorSeed) -> SourceResult:
        search_params = {
            "db": "pubmed",
            "term": f"{seed.name}[Author]",
            "retmode": "json",
            "retmax": "25",
        }
        if self.api_key:
            search_params["api_key"] = self.api_key
        search = await self.crawler.fetch(PUBMED_SEARCH, params=search_params)
        if search.status is not SourceStatus.OK:
            return SourceResult(self.name, search.status, error=search.error)
        try:
            ids = decode_json(search.body)["esearchresult"]["idlist"]
            if not isinstance(ids, list):
                raise ValueError
        except (KeyError, TypeError, UnicodeError, ValueError):
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_search_response",
            )
        if not ids:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)

        summary_params = {
            "db": "pubmed",
            "id": ",".join(str(item) for item in ids),
            "retmode": "json",
        }
        if self.api_key:
            summary_params["api_key"] = self.api_key
        summary = await self.crawler.fetch(
            PUBMED_SUMMARY, params=summary_params
        )
        if summary.status is not SourceStatus.OK:
            return SourceResult(self.name, summary.status, error=summary.error)
        try:
            result = decode_json(summary.body)["result"]
            uids = result["uids"]
        except (KeyError, TypeError, UnicodeError, ValueError):
            return SourceResult(
                self.name,
                SourceStatus.SOURCE_UNAVAILABLE,
                error="malformed_summary_response",
            )

        items = []
        for uid in uids:
            record = result.get(str(uid))
            if not isinstance(record, dict):
                continue
            pmid = str(record.get("uid") or uid)
            candidate_id = f"pubmed:{pmid}"
            profile_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            items.append(
                evidence(
                    source=self.name,
                    field="pmid",
                    value=pmid,
                    url=profile_url,
                    candidate_id=candidate_id,
                )
            )
            if record.get("title"):
                items.append(
                    evidence(
                        source=self.name,
                        field="paper_title",
                        value=record["title"],
                        url=profile_url,
                        candidate_id=candidate_id,
                        metadata={
                            "publication_date": record.get("pubdate"),
                            "journal": record.get("source"),
                        },
                    )
                )
            for author in record.get("authors") or []:
                if isinstance(author, dict) and author.get("name"):
                    items.append(
                        evidence(
                            source=self.name,
                            field="contributor_name",
                            value=author["name"],
                            url=profile_url,
                            candidate_id=candidate_id,
                        )
                    )
            for identifier in record.get("articleids") or []:
                if not isinstance(identifier, dict) or not identifier.get("value"):
                    continue
                id_type = str(identifier.get("idtype", "")).casefold()
                if id_type not in {"doi", "orcid"}:
                    continue
                value = identifier["value"]
                url = (
                    f"https://doi.org/{value}"
                    if id_type == "doi"
                    else f"https://orcid.org/{value}"
                )
                items.append(
                    evidence(
                        source=self.name,
                        field=id_type,
                        value=value,
                        url=url,
                        candidate_id=candidate_id,
                    )
                )
        if not items:
            return SourceResult(self.name, SourceStatus.NOT_FOUND)
        return SourceResult(self.name, SourceStatus.OK, tuple(items))
