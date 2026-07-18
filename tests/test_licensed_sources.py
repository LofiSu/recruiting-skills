from researcher_recruiting.sources.licensed import licensed_source_descriptors


def test_unlicensed_platforms_are_locator_only(settings):
    descriptors = licensed_source_descriptors(settings)
    assert descriptors["scopus"].mode == "locator_only"
    assert descriptors["web_of_science"].mode == "locator_only"
    assert all(item.official_api_only for item in descriptors.values())
    assert {
        "scopus",
        "web_of_science",
        "dimensions",
        "lens",
        "nasa_ads",
        "ieee_xplore",
        "springer_nature",
    } == set(descriptors)


def test_licensed_descriptors_do_not_make_requests(settings):
    descriptors = licensed_source_descriptors(settings)
    assert all(item.locator_url_template.startswith("https://") for item in descriptors.values())
    assert not any(hasattr(item, "fetch") for item in descriptors.values())
