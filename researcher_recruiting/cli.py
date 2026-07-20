import argparse
import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Sequence

import httpx

from researcher_recruiting.cache import SqliteCache
from researcher_recruiting.config import Settings
from researcher_recruiting.crawling import HttpCrawler
from researcher_recruiting.exporters import write_artifacts
from researcher_recruiting.pipeline import ResearchPipeline
from researcher_recruiting.source_registry import SourceRegistry
from researcher_recruiting.sources.arxiv import PaperNotFound, resolve_paper
from researcher_recruiting.sources.crossref import CrossrefSource
from researcher_recruiting.sources.datacite import DataCiteSource
from researcher_recruiting.sources.dblp import DblpSource
from researcher_recruiting.sources.europe_pmc import EuropePmcSource
from researcher_recruiting.sources.github import GitHubSource
from researcher_recruiting.sources.inspire import InspireSource
from researcher_recruiting.sources.opencitations import OpenCitationsEnricher
from researcher_recruiting.sources.openalex import OpenAlexSource
from researcher_recruiting.sources.openreview import OpenReviewSource
from researcher_recruiting.sources.orcid import (
    HttpxOrcidTokenProvider,
    OrcidSource,
)
from researcher_recruiting.sources.public_web import PublicWebSource
from researcher_recruiting.sources.pubmed import PubmedSource
from researcher_recruiting.sources.ror import RorSource
from researcher_recruiting.sources.semantic_scholar import (
    SemanticScholarSource,
)
from researcher_recruiting.sources.unpaywall import UnpaywallEnricher
from researcher_recruiting.sources.wikidata import WikidataSource


def build_pipeline(settings: Settings) -> ResearchPipeline:
    try:
        cache = SqliteCache(settings.cache_path)
    except OSError:
        fallback_cache = (
            Path(tempfile.gettempdir())
            / "researcher-recruiting-skill"
            / "cache.sqlite3"
        )
        cache = SqliteCache(fallback_cache)
    crawler = HttpCrawler(settings, cache)
    sources = {
        "openalex": OpenAlexSource(crawler, settings.openalex_api_key),
        "crossref": CrossrefSource(crawler, settings.crossref_mailto),
        "semantic_scholar": SemanticScholarSource(
            crawler, settings.semantic_scholar_api_key
        ),
        "orcid": OrcidSource(
            crawler,
            HttpxOrcidTokenProvider(),
            settings.orcid_client_id,
            settings.orcid_client_secret,
        ),
        "datacite": DataCiteSource(crawler),
        "ror": RorSource(crawler),
        "wikidata": WikidataSource(crawler),
        "github": GitHubSource(crawler, settings.github_token),
        "openreview": OpenReviewSource(crawler),
        "dblp": DblpSource(crawler),
        "pubmed": PubmedSource(crawler, settings.ncbi_api_key),
        "europe_pmc": EuropePmcSource(crawler),
        "inspire": InspireSource(crawler),
    }
    registry = SourceRegistry(sources=sources)

    async def paper_resolver(value: str):
        proxy = settings.https_proxy or settings.http_proxy
        async with httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
            proxy=proxy,
        ) as client:
            return await resolve_paper(value, client)

    return ResearchPipeline(
        paper_resolver=paper_resolver,
        source_registry=registry,
        work_enrichers=(
            OpenCitationsEnricher(crawler),
            UnpaywallEnricher(crawler, settings.unpaywall_email),
        ),
        public_web_source=PublicWebSource(crawler),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="researcher-recruiting",
        description=(
            "Build an evidence-backed public researcher recruiting report."
        ),
    )
    parser.add_argument("paper", help="arXiv id, URL, or exact paper title")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results"),
        help="report output root (default: ./results)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="bypass cached source responses",
    )
    parser.add_argument(
        "--sources",
        default="",
        help="comma-separated additional source names",
    )
    return parser


async def run_cli(argv: Sequence[str]) -> int:
    try:
        args = _parser().parse_args(list(argv))
    except SystemExit as error:
        return int(error.code or 0)
    requested_sources = tuple(
        item.strip()
        for item in args.sources.split(",")
        if item.strip()
    )
    try:
        pipeline = build_pipeline(Settings.from_env())
        if requested_sources:
            result = await pipeline.run(
                args.paper,
                refresh=args.refresh,
                requested_sources=requested_sources,
            )
        else:
            result = await pipeline.run(
                args.paper,
                refresh=args.refresh,
            )
    except PaperNotFound:
        print(
            f"Could not resolve paper: {args.paper}",
            file=sys.stderr,
        )
        return 2
    except ValueError as error:
        print(f"Invalid input: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        print(
            f"Internal pipeline error: {type(error).__name__}",
            file=sys.stderr,
        )
        return 4
    try:
        run_directory = write_artifacts(result, args.output)
    except OSError as error:
        print(
            f"Could not write report: {type(error).__name__}",
            file=sys.stderr,
        )
        return 3
    except Exception as error:
        print(
            f"Report invariant failure: {type(error).__name__}",
            file=sys.stderr,
        )
        return 4
    print(run_directory)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run_cli(sys.argv[1:])))
