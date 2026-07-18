import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_cache_dir


@dataclass(frozen=True)
class Settings:
    cache_path: Path
    user_agent: str
    github_token: str | None
    semantic_scholar_api_key: str | None
    openalex_api_key: str | None
    ncbi_api_key: str | None
    unpaywall_email: str | None
    crossref_mailto: str | None
    orcid_client_id: str | None
    orcid_client_secret: str | None
    http_proxy: str | None
    https_proxy: str | None
    request_timeout_seconds: float = 15.0
    max_response_bytes: int = 2_000_000

    @classmethod
    def from_env(cls) -> "Settings":
        default_cache = Path(user_cache_dir("researcher-recruiting-skill"))
        return cls(
            cache_path=Path(
                os.getenv(
                    "RESEARCHER_RECRUITING_CACHE",
                    default_cache / "cache.sqlite3",
                )
            ),
            user_agent=os.getenv(
                "RESEARCHER_RECRUITING_USER_AGENT",
                "researcher-recruiting-skill/0.1 (+public-research-enrichment)",
            ),
            github_token=os.getenv("GITHUB_TOKEN"),
            semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
            openalex_api_key=os.getenv("OPENALEX_API_KEY"),
            ncbi_api_key=os.getenv("NCBI_API_KEY"),
            unpaywall_email=os.getenv("UNPAYWALL_EMAIL"),
            crossref_mailto=os.getenv("CROSSREF_MAILTO"),
            orcid_client_id=os.getenv("ORCID_CLIENT_ID"),
            orcid_client_secret=os.getenv("ORCID_CLIENT_SECRET"),
            http_proxy=os.getenv("HTTP_PROXY"),
            https_proxy=os.getenv("HTTPS_PROXY"),
        )
