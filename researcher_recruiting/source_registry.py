from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

ALWAYS_ON = (
    "openalex",
    "crossref",
    "semantic_scholar",
    "orcid",
    "datacite",
    "ror",
    "wikidata",
    "github",
    "openreview",
)

CATEGORY_ROUTES = {
    "cs.": ("dblp",),
    "stat.ML": ("dblp",),
    "eess.": ("dblp",),
    "q-bio.": ("pubmed", "europe_pmc"),
    "hep-": ("inspire",),
    "nucl-": ("inspire",),
}


@dataclass(frozen=True)
class SourceRegistry:
    sources: Mapping[str, Any]
    always_on: Sequence[str] = ALWAYS_ON
    category_routes: Mapping[str, Sequence[str]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.category_routes is None:
            object.__setattr__(self, "category_routes", CATEGORY_ROUTES)

    def selected_names(
        self,
        categories: Sequence[str],
        requested: Sequence[str] = (),
    ) -> tuple[str, ...]:
        unknown = [name for name in requested if name not in self.sources]
        if unknown:
            raise ValueError(f"unknown source: {', '.join(unknown)}")

        selected = []

        def add(name: str) -> None:
            if name in self.sources and name not in selected:
                selected.append(name)

        for name in self.always_on:
            add(name)
        for category in categories:
            for prefix, names in self.category_routes.items():
                if category == prefix or category.startswith(prefix):
                    for name in names:
                        add(name)
        for name in requested:
            add(name)
        return tuple(selected)

    def select(
        self,
        categories: Sequence[str],
        requested: Sequence[str] = (),
    ) -> tuple[Any, ...]:
        return tuple(
            self.sources[name]
            for name in self.selected_names(categories, requested=requested)
        )
