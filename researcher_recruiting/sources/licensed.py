import os
from dataclasses import dataclass
from typing import Collection

from researcher_recruiting.config import Settings


@dataclass(frozen=True)
class LicensedSourceDescriptor:
    name: str
    credential_env: str
    official_api_only: bool
    mode: str
    locator_url_template: str


_LICENSED_SOURCES = {
    "scopus": (
        "SCOPUS_API_KEY",
        "https://www.scopus.com/results/authorNamesList.uri?name={query}",
    ),
    "web_of_science": (
        "WEB_OF_SCIENCE_API_KEY",
        "https://www.webofscience.com/wos/author/search?name={query}",
    ),
    "dimensions": (
        "DIMENSIONS_API_KEY",
        "https://app.dimensions.ai/discover/publication?search_text={query}",
    ),
    "lens": (
        "LENS_API_TOKEN",
        "https://www.lens.org/lens/search/scholar/list?q={query}",
    ),
    "nasa_ads": (
        "NASA_ADS_TOKEN",
        "https://ui.adsabs.harvard.edu/search/q=author%3A%22{query}%22",
    ),
    "ieee_xplore": (
        "IEEE_XPLORE_API_KEY",
        "https://ieeexplore.ieee.org/search/searchresult.jsp?queryText={query}",
    ),
    "springer_nature": (
        "SPRINGER_NATURE_API_KEY",
        "https://link.springer.com/search?query={query}",
    ),
}


def licensed_source_descriptors(
    settings: Settings,
    registered_adapters: Collection[str] = (),
) -> dict[str, LicensedSourceDescriptor]:
    del settings
    return {
        name: LicensedSourceDescriptor(
            name=name,
            credential_env=credential_env,
            official_api_only=True,
            mode=(
                "authorized_api"
                if name in registered_adapters and os.getenv(credential_env)
                else "locator_only"
            ),
            locator_url_template=locator,
        )
        for name, (credential_env, locator) in _LICENSED_SOURCES.items()
    }
