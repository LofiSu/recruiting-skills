from researcher_recruiting.models import AuthorSeed
from researcher_recruiting.search_links import build_locator_links


def test_locator_links_encode_name_and_affiliation():
    links = build_locator_links(
        AuthorSeed(
            name="Ada Lovelace", affiliation="Analytical Engines"
        )
    )
    assert {
        "google_scholar",
        "researchgate",
        "academia",
        "linkedin",
        "maimai",
        "scopus",
        "web_of_science",
        "dimensions",
        "lens",
        "nasa_ads",
        "ieee_xplore",
        "springer_nature",
    } <= set(links)
    assert "Ada+Lovelace" in links["google_scholar"]
    assert "Analytical+Engines" in links["linkedin"]


def test_locator_links_are_search_urls_not_profile_guesses():
    links = build_locator_links(AuthorSeed(name="Ada Lovelace"))
    assert "linkedin.com/in/ada" not in links["linkedin"]
    assert "maimai.cn/contact" not in links["maimai"]
