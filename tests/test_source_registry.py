import pytest

from researcher_recruiting.source_registry import SourceRegistry


def build_test_registry():
    return SourceRegistry(
        sources={
            "openalex": object(),
            "crossref": object(),
            "dblp": object(),
            "pubmed": object(),
            "europe_pmc": object(),
        },
        always_on=("openalex", "crossref"),
        category_routes={
            "cs.": ("dblp",),
            "q-bio.": ("pubmed", "europe_pmc"),
        },
    )


def test_registry_selects_always_on_and_cs_sources():
    registry = build_test_registry()
    assert registry.selected_names(("cs.CL",)) == (
        "openalex",
        "crossref",
        "dblp",
    )


def test_registry_does_not_run_biomedical_sources_for_math():
    registry = build_test_registry()
    assert "pubmed" not in registry.selected_names(("math.OC",))


def test_registry_accepts_explicit_source_override():
    registry = build_test_registry()
    assert "dblp" in registry.selected_names(
        ("math.OC",), requested=("dblp",)
    )


def test_registry_rejects_unknown_explicit_source():
    registry = build_test_registry()
    with pytest.raises(ValueError, match="unknown source"):
        registry.selected_names(("cs.CL",), requested=("made_up",))


def test_registry_returns_sources_in_selected_order():
    registry = build_test_registry()
    assert registry.select(("cs.CL",)) == tuple(
        registry.sources[name]
        for name in ("openalex", "crossref", "dblp")
    )
