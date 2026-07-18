from urllib.parse import quote_plus

from researcher_recruiting.models import AuthorSeed


def build_locator_links(seed: AuthorSeed) -> dict[str, str]:
    query = " ".join(
        part for part in (seed.name, seed.affiliation or "") if part
    )
    encoded = quote_plus(query)
    return {
        "google_scholar": (
            f"https://scholar.google.com/scholar?q={encoded}"
        ),
        "researchgate": (
            "https://www.google.com/search?q="
            f"site%3Aresearchgate.net+{encoded}"
        ),
        "academia": (
            "https://www.google.com/search?q="
            f"site%3Aacademia.edu+{encoded}"
        ),
        "linkedin": (
            "https://www.google.com/search?q="
            f"site%3Alinkedin.com%2Fin+{encoded}"
        ),
        "maimai": (
            f"https://www.baidu.com/s?wd=site%3Amaimai.cn+{encoded}"
        ),
        "scopus": (
            f"https://www.google.com/search?q=site%3Ascopus.com+{encoded}"
        ),
        "web_of_science": (
            "https://www.google.com/search?q="
            f"site%3Awebofscience.com+{encoded}"
        ),
        "dimensions": (
            "https://www.google.com/search?q="
            f"site%3Adimensions.ai+{encoded}"
        ),
        "lens": (
            f"https://www.google.com/search?q=site%3Alens.org+{encoded}"
        ),
        "nasa_ads": (
            "https://www.google.com/search?q="
            f"site%3Aui.adsabs.harvard.edu+{encoded}"
        ),
        "ieee_xplore": (
            "https://www.google.com/search?q="
            f"site%3Aieeexplore.ieee.org+{encoded}"
        ),
        "springer_nature": (
            "https://www.google.com/search?q="
            f"site%3Alink.springer.com+{encoded}"
        ),
    }
