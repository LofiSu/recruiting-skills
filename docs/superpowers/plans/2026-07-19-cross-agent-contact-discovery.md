# Cross-Agent Contact Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add evidence-backed public professional contact discovery for every paper author and make the repository usable by any Agent Skills-compatible agent.

**Architecture:** Keep the Python CLI as the deterministic source of record. Add structured contact models and a focused contact aggregation module, scope source outcomes to authors in the pipeline, extend the existing five artifacts, then rewrite the Skill instructions as platform-neutral Agent Skills guidance with optional platform installation examples.

**Tech Stack:** Python 3.11+, frozen dataclasses, `httpx`, Beautiful Soup, `pytest`, Agent Skills `SKILL.md`

## Global Constraints

- Include every paper author exactly once and in paper order.
- Collect only public professional contact routes; never guess emails or collect private phone numbers, home addresses, breached data, or broker data.
- Keep Google Scholar, LinkedIn, Maimai, ResearchGate, Academia.edu, and unlicensed commercial indexes locator-only.
- Require no commercial API, hosted service, MCP server, browser, Codex tool, or Claude Code tool.
- Preserve exactly five output artifacts: `report.md`, `candidates.csv`, `candidates.json`, `evidence.json`, and `run-log.json`.
- Treat source failures as partial results unless the paper or trustworthy author list cannot be resolved.
- Use Python 3.11 or newer and preserve existing dependency upper bounds.
- Follow test-first RED-GREEN-REFACTOR for every behavior change.

## File Map

- Modify `researcher_recruiting/models.py`: contact enums, contact point model, author-scoped source result, and contact fields on identity matches.
- Create `researcher_recruiting/contacts.py`: normalize, deduplicate, gate, and status public contact points.
- Modify `researcher_recruiting/sources/public_web.py`: public email normalization and same-origin contact-form discovery.
- Modify `researcher_recruiting/sources/github.py`: label public GitHub contact evidence.
- Modify `researcher_recruiting/sources/orcid.py`: label explicitly public ORCID contact evidence.
- Modify `researcher_recruiting/pipeline.py`: scope source outcomes per author and attach contact summaries after identity resolution.
- Modify `researcher_recruiting/exporters.py`: export contact status, structured points, primary fields, and per-author source attempts.
- Modify `SKILL.md`: platform-neutral Agent Skills workflow.
- Create `references/installation.md`: generic and optional platform-specific installation paths.
- Modify `README.md`: user-facing generic, Claude Code, Codex, OpenCode, and standalone CLI setup.
- Modify `agents/openai.yaml`: keep optional OpenAI metadata aligned with the generic Skill.
- Modify `pyproject.toml`: release version `0.2.0`.
- Create `tests/test_contacts.py`: contact normalization, deduplication, identity gating, and status tests.
- Modify `tests/test_models.py`, `tests/test_public_web.py`, `tests/test_identity_sources.py`, `tests/test_pipeline.py`, `tests/test_exporters.py`, and `tests/skill-cases.md`.
- Create `tests/test_skill_portability.py`: enforce Agent Skills portability and prohibit platform-specific core instructions.

---

### Task 1: Structured Contact Model and Aggregation

**Files:**
- Modify: `researcher_recruiting/models.py`
- Create: `researcher_recruiting/contacts.py`
- Create: `tests/test_contacts.py`
- Modify: `tests/test_models.py`

**Interfaces:**
- Consumes: `IdentityMatch`, `IdentityState`, `Evidence`, `SourceResult`, and `AuthorSeed`.
- Produces: `ContactKind`, `ContactStatus`, `ContactPoint`, `build_contact_points(match) -> tuple[ContactPoint, ...]`, `calculate_contact_status(match, points, source_results) -> ContactStatus`, and `attach_contacts(match, source_results) -> IdentityMatch`.

- [ ] **Step 1: Write failing model and aggregation tests**

Add these representative tests to `tests/test_contacts.py`:

```python
from researcher_recruiting.contacts import attach_contacts
from researcher_recruiting.models import (
    AuthorSeed,
    ContactKind,
    ContactStatus,
    Evidence,
    IdentityMatch,
    IdentityState,
    SourceResult,
    SourceStatus,
)


def item(field, value, source="github", url="https://example.test/profile"):
    return Evidence(
        source=source,
        field=field,
        value=value,
        url=url,
        collected_at="2026-07-19T00:00:00Z",
        candidate_id="candidate:ada",
        metadata={"visibility": "public_professional"},
    )


def match(state=IdentityState.PROBABLE, evidence=()):
    return IdentityMatch(
        author=AuthorSeed(
            name="Ada Lovelace",
            affiliation="Analytical Engines",
        ),
        state=state,
        confidence=70,
        reasons=("paper overlap",),
        evidence=tuple(evidence),
    )


def test_contacts_deduplicate_normalized_public_email_and_keep_evidence():
    result = attach_contacts(
        match(
            evidence=(
                item("email", " Ada@Example.org "),
                item(
                    "email",
                    "ada@example.org",
                    source="orcid",
                    url="https://orcid.org/0000",
                ),
            )
        ),
        (
            SourceResult("github", SourceStatus.OK),
            SourceResult("orcid", SourceStatus.OK),
        ),
    )
    emails = [
        point
        for point in result.contact_points
        if point.kind is ContactKind.PROFESSIONAL_EMAIL
    ]
    assert len(emails) == 1
    assert emails[0].value == "ada@example.org"
    assert len(emails[0].evidence) == 2
    assert emails[0].direct is True
    assert result.contact_status is ContactStatus.FOUND


def test_ambiguous_identity_does_not_promote_direct_contact():
    result = attach_contacts(
        match(
            state=IdentityState.AMBIGUOUS,
            evidence=(item("email", "ada@example.org"),),
        ),
        (SourceResult("github", SourceStatus.OK),),
    )
    email = next(
        point
        for point in result.contact_points
        if point.kind is ContactKind.PROFESSIONAL_EMAIL
    )
    assert email.direct is False
    assert result.contact_status is ContactStatus.AMBIGUOUS


def test_locator_links_do_not_count_as_found():
    result = attach_contacts(
        match(state=IdentityState.NOT_FOUND),
        (
            SourceResult("github", SourceStatus.NOT_FOUND),
            SourceResult("openreview", SourceStatus.NOT_FOUND),
            SourceResult("orcid", SourceStatus.NOT_FOUND),
            SourceResult("public_web", SourceStatus.NOT_FOUND),
        ),
    )
    assert {
        ContactKind.GOOGLE_SCHOLAR_LOCATOR,
        ContactKind.LINKEDIN_LOCATOR,
        ContactKind.MAIMAI_LOCATOR,
    } <= {point.kind for point in result.contact_points}
    assert result.contact_status is ContactStatus.NOT_FOUND


def test_unavailable_direct_source_is_distinct_from_not_found():
    result = attach_contacts(
        match(state=IdentityState.NOT_FOUND),
        (
            SourceResult("github", SourceStatus.SOURCE_UNAVAILABLE),
            SourceResult("openreview", SourceStatus.NOT_FOUND),
            SourceResult("orcid", SourceStatus.NOT_FOUND),
            SourceResult("public_web", SourceStatus.NOT_FOUND),
        ),
    )
    assert result.contact_status is ContactStatus.SOURCES_UNAVAILABLE
```

Extend `tests/test_models.py` with a frozen contact point construction test.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python -m pytest tests/test_contacts.py tests/test_models.py -v
```

Expected: collection fails because `ContactKind`, `ContactStatus`, and
`ContactPoint` do not exist.

- [ ] **Step 3: Add the contact types to `models.py`**

Add:

```python
class ContactKind(str, Enum):
    PROFESSIONAL_EMAIL = "professional_email"
    CONTACT_FORM = "contact_form"
    HOMEPAGE = "homepage"
    GITHUB = "github"
    OPENREVIEW = "openreview"
    GOOGLE_SCHOLAR_LOCATOR = "google_scholar_locator"
    LINKEDIN_LOCATOR = "linkedin_locator"
    MAIMAI_LOCATOR = "maimai_locator"


class ContactStatus(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    SOURCES_UNAVAILABLE = "sources_unavailable"


@dataclass(frozen=True)
class ContactPoint:
    kind: ContactKind
    value: str
    source: str
    source_url: str
    collected_at: str
    confidence: int
    direct: bool
    evidence: tuple["Evidence", ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)
```

Append `author_name: str | None = None` to `SourceResult`. Append these
backward-compatible defaults to `IdentityMatch`:

```python
contact_status: ContactStatus = ContactStatus.NOT_FOUND
contact_points: tuple[ContactPoint, ...] = ()
```

- [ ] **Step 4: Implement `contacts.py`**

Implement a focused module with:

```python
from dataclasses import replace

from researcher_recruiting.models import (
    ContactKind,
    ContactPoint,
    ContactStatus,
    IdentityMatch,
    IdentityState,
    SourceResult,
    SourceStatus,
)
from researcher_recruiting.search_links import build_locator_links

_FIELD_KINDS = {
    "email": ContactKind.PROFESSIONAL_EMAIL,
    "contact_form": ContactKind.CONTACT_FORM,
    "homepage": ContactKind.HOMEPAGE,
    "github": ContactKind.GITHUB,
    "openreview": ContactKind.OPENREVIEW,
}
_LOCATOR_KINDS = {
    "google_scholar": ContactKind.GOOGLE_SCHOLAR_LOCATOR,
    "linkedin": ContactKind.LINKEDIN_LOCATOR,
    "maimai": ContactKind.MAIMAI_LOCATOR,
}
_DIRECT_SOURCE_NAMES = {"github", "openreview", "orcid", "public_web"}
_UNAVAILABLE = {
    SourceStatus.SOURCE_UNAVAILABLE,
    SourceStatus.BLOCKED_BY_ROBOTS,
}


def _normalized(kind: ContactKind, value: str) -> str:
    value = value.strip()
    if kind is ContactKind.PROFESSIONAL_EMAIL:
        return value.casefold()
    return value.rstrip("/")


def build_contact_points(match: IdentityMatch) -> tuple[ContactPoint, ...]:
    grouped = {}
    identity_is_usable = match.state in {
        IdentityState.CONFIRMED,
        IdentityState.PROBABLE,
    }
    for evidence in match.evidence:
        kind = _FIELD_KINDS.get(evidence.field)
        if kind is None or not evidence.value.strip():
            continue
        value = (
            evidence.url
            if kind in {ContactKind.GITHUB, ContactKind.OPENREVIEW}
            else evidence.value
        )
        normalized = _normalized(kind, value)
        key = (kind, normalized)
        grouped.setdefault(key, []).append(evidence)

    points = []
    for (kind, value), evidence_items in grouped.items():
        first = evidence_items[0]
        direct_kind = kind in {
            ContactKind.PROFESSIONAL_EMAIL,
            ContactKind.CONTACT_FORM,
        }
        points.append(
            ContactPoint(
                kind=kind,
                value=value,
                source=first.source,
                source_url=first.url,
                collected_at=first.collected_at,
                confidence=match.confidence,
                direct=direct_kind and identity_is_usable,
                evidence=tuple(evidence_items),
                metadata={"identity_state": match.state.value},
            )
        )
    for locator_name, kind in _LOCATOR_KINDS.items():
        url = build_locator_links(match.author)[locator_name]
        points.append(
            ContactPoint(
                kind=kind,
                value=url,
                source="locator_links",
                source_url=url,
                collected_at="",
                confidence=0,
                direct=False,
                metadata={"mode": "locator_only"},
            )
        )
    return tuple(points)


def calculate_contact_status(
    match: IdentityMatch,
    points: tuple[ContactPoint, ...],
    source_results: tuple[SourceResult, ...],
) -> ContactStatus:
    verified = [
        point
        for point in points
        if point.kind not in set(_LOCATOR_KINDS.values())
    ]
    if verified and match.state in {
        IdentityState.CONFIRMED,
        IdentityState.PROBABLE,
    }:
        return ContactStatus.FOUND
    if verified or match.state is IdentityState.AMBIGUOUS:
        return ContactStatus.AMBIGUOUS
    applicable = [
        result
        for result in source_results
        if result.source in _DIRECT_SOURCE_NAMES
    ]
    if any(result.status in _UNAVAILABLE for result in applicable):
        return ContactStatus.SOURCES_UNAVAILABLE
    return ContactStatus.NOT_FOUND


def attach_contacts(
    match: IdentityMatch,
    source_results: tuple[SourceResult, ...],
) -> IdentityMatch:
    points = build_contact_points(match)
    return replace(
        match,
        contact_points=points,
        contact_status=calculate_contact_status(
            match, points, source_results
        ),
    )
```

During implementation, keep locator timestamps deterministic by accepting a
timestamp helper or using the existing `collected_at()` helper; tests should
assert a non-empty UTC timestamp rather than rely on an empty value.

- [ ] **Step 5: Run focused and model tests**

Run:

```bash
python -m pytest tests/test_contacts.py tests/test_models.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add researcher_recruiting/models.py researcher_recruiting/contacts.py tests/test_contacts.py tests/test_models.py
git commit -m "feat: model public author contact routes"
```

---

### Task 2: Public Contact Evidence Extraction

**Files:**
- Modify: `researcher_recruiting/sources/public_web.py`
- Modify: `researcher_recruiting/sources/github.py`
- Modify: `researcher_recruiting/sources/orcid.py`
- Modify: `tests/test_public_web.py`
- Modify: `tests/test_identity_sources.py`
- Modify: `tests/fixtures/public_homepage.html`

**Interfaces:**
- Consumes: existing `Evidence` field/value/url/metadata contract.
- Produces: normalized `email` evidence with
  `metadata["visibility"] == "public_professional"` and same-origin
  `contact_form` evidence.

- [ ] **Step 1: Add failing extraction tests**

Add tests that assert:

```python
@pytest.mark.asyncio
async def test_public_homepage_normalizes_email_and_finds_contact_form():
    url = "https://university.example/~ada/"
    html = (
        '<a href="mailto:%20Ada@Example.org?subject=Research">'
        "Email</a>"
        '<a href="/contact/">Contact Ada</a>'
        '<a href="https://external.example/contact">External contact</a>'
    )
    crawler = StubCrawler({url: [html_result(url, html)]})
    result = await PublicWebSource(crawler).enrich_urls((url,))
    email = next(item for item in result.evidence if item.field == "email")
    form = next(
        item for item in result.evidence if item.field == "contact_form"
    )
    assert email.value == "ada@example.org"
    assert email.metadata["visibility"] == "public_professional"
    assert form.value == "https://university.example/contact/"
    assert not any(
        item.value == "https://external.example/contact"
        for item in result.evidence
    )
```

Extend the GitHub and ORCID tests to assert public email evidence contains the
same visibility metadata.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python -m pytest tests/test_public_web.py tests/test_identity_sources.py -v
```

Expected: FAIL because mailto values are not percent-decoded or normalized,
contact forms are not emitted, and visibility metadata is absent.

- [ ] **Step 3: Implement bounded public contact extraction**

In `public_web.py`, add a strict email normalizer using `unquote` and a
full-match email pattern. For same-origin anchors, emit `contact_form` only
when the path or normalized anchor text contains `contact`, and do not follow
the form URL:

```python
_EMAIL_PATTERN = re.compile(
    r"[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+",
    re.IGNORECASE,
)


def _public_email(href: str) -> str | None:
    value = unquote(href.split(":", 1)[1].split("?", 1)[0]).strip()
    return value.casefold() if _EMAIL_PATTERN.fullmatch(value) else None
```

Attach `{"visibility": "public_professional"}` to public-web, GitHub, and
explicitly public ORCID email evidence. Preserve GitHub and ORCID's existing
source-level public visibility requirements.

- [ ] **Step 4: Run focused source tests**

Run:

```bash
python -m pytest tests/test_public_web.py tests/test_identity_sources.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add researcher_recruiting/sources/public_web.py researcher_recruiting/sources/github.py researcher_recruiting/sources/orcid.py tests/test_public_web.py tests/test_identity_sources.py tests/fixtures/public_homepage.html
git commit -m "feat: extract public professional contact evidence"
```

---

### Task 3: Author-Scoped Pipeline Contact Summaries

**Files:**
- Modify: `researcher_recruiting/pipeline.py`
- Modify: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `attach_contacts(match, source_results) -> IdentityMatch` from
  Task 1.
- Produces: every `SourceResult.author_name` is set by the pipeline, and every
  returned `IdentityMatch` has contact points and contact status.

- [ ] **Step 1: Add failing pipeline tests**

Add:

```python
@pytest.mark.asyncio
async def test_pipeline_scopes_source_attempts_and_contacts_to_each_author(
    fake_paper, evidence_factory
):
    github = StaticSource(
        "github",
        SourceResult(
            "github",
            SourceStatus.OK,
            evidence=(
                evidence_factory(
                    field="name",
                    value="Ada Lovelace",
                    source="github",
                ),
                evidence_factory(
                    field="paper_title",
                    value=fake_paper.title,
                    source="github",
                ),
                evidence_factory(
                    field="orcid",
                    value="0000-0001-2345-6789",
                    source="github",
                ),
                evidence_factory(
                    field="email",
                    value="ada@university.example",
                    source="github",
                ),
            ),
        ),
    )
    pipeline = ResearchPipeline(
        paper_resolver=AsyncMock(return_value=fake_paper),
        source_registry=RecordingRegistry(selected=(github,)),
        work_enrichers=(),
        public_web_source=FakePublicWebSource(),
    )
    result = await pipeline.run("1706.03762")
    assert [match.author.name for match in result.matches] == [
        author.name for author in fake_paper.authors
    ]
    assert all(source.author_name for source in result.source_results)
    ada = result.matches[0]
    assert ada.contact_status is ContactStatus.FOUND
    assert any(
        point.kind is ContactKind.PROFESSIONAL_EMAIL
        for point in ada.contact_points
    )
```

Add a second test proving an unavailable GitHub source yields
`SOURCES_UNAVAILABLE` for that author without removing either author.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python -m pytest tests/test_pipeline.py -v
```

Expected: FAIL because source results are not author-scoped and contacts are
not attached.

- [ ] **Step 3: Scope results and attach contacts**

Import `dataclasses.replace` and `attach_contacts`. Add:

```python
@staticmethod
def _scope_result(result: SourceResult, seed: AuthorSeed) -> SourceResult:
    return replace(result, author_name=seed.name)
```

Apply `_scope_result` to every author source, work enricher, public-web, and
locator result before appending it. After `resolve_identity`, run:

```python
identity_evidence = tuple(
    item
    for item in evidence_items
    if item.metadata.get("mode") != "locator_only"
)
match = resolve_identity(
    seed,
    identity_evidence,
    unavailable_sources=unavailable,
)
scoped_results = tuple(source_results)
match = attach_contacts(match, scoped_results)
return match, scoped_results
```

Replace the existing `resolve_identity` call rather than calling it twice.
This prevents locator-only evidence from changing an otherwise `not_found`
identity into `ambiguous`. Do not change the outer `asyncio.gather` ordering;
it already preserves paper author order.

- [ ] **Step 4: Run focused and regression pipeline tests**

Run:

```bash
python -m pytest tests/test_pipeline.py tests/test_identity.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add researcher_recruiting/pipeline.py tests/test_pipeline.py
git commit -m "feat: attach author-scoped contact summaries"
```

---

### Task 4: Contact-First Artifacts and Per-Author Run Log

**Files:**
- Modify: `researcher_recruiting/exporters.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_exporters.py`
- Modify: `tests/test_network_e2e.py`

**Interfaces:**
- Consumes: `IdentityMatch.contact_status`,
  `IdentityMatch.contact_points`, and `SourceResult.author_name`.
- Produces: backward-compatible five artifacts with contact-first fields and
  per-author source attempts.

- [ ] **Step 1: Add failing exporter tests**

Update the `run_result` fixture with one direct email, one contact form, and
three locators. Add assertions:

```python
def test_candidates_export_structured_contacts_and_status(
    tmp_path, run_result
):
    run_dir = write_artifacts(run_result, tmp_path)
    candidates = json.loads(
        (run_dir / "candidates.json").read_text(encoding="utf-8")
    )
    record = candidates[0]
    assert record["contact_status"] == "found"
    assert record["email"] == "ada@university.example"
    assert record["contact_form"] == "https://example.test/contact"
    assert {
        point["kind"] for point in record["contact_points"]
    } >= {
        "professional_email",
        "google_scholar_locator",
        "linkedin_locator",
        "maimai_locator",
    }


def test_run_log_groups_source_attempts_by_author(tmp_path, run_result):
    run_dir = write_artifacts(run_result, tmp_path)
    log = json.loads(
        (run_dir / "run-log.json").read_text(encoding="utf-8")
    )
    author = log["authors"][0]
    assert author["author_name"] == "Ada Lovelace"
    assert author["contact_status"] == "found"
    assert {attempt["status"] for attempt in author["source_attempts"]} == {
        "ok"
    }
```

Add a report assertion that every candidate section includes `Contact status`
and either public contact routes or the explicit no-contact explanation.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python -m pytest tests/test_exporters.py tests/test_network_e2e.py -m "not network" -v
```

Expected: FAIL because contact fields and per-author source attempts are not
exported.

- [ ] **Step 3: Extend candidate records and CSV**

Add `contact_status` and `contact_form` to `CSV_COLUMNS`. Keep the existing
`email` column as the primary public professional email for backward
compatibility. In `_candidate_records`, select primary values from
`match.contact_points`, include `_jsonable(match.contact_points)`, and include
the core locator values from those points.

Primary selection must accept only points where `direct is True` for email and
contact form. Homepage, GitHub, and OpenReview may be shown as verified public
profiles even though they are not direct routes.

- [ ] **Step 4: Extend Markdown and run log**

For every author section, render:

```markdown
- Contact status: `found`
- Direct public contacts: [email](mailto:...), [contact form](...)
- Public profiles: [Homepage](...), [GitHub](...), [OpenReview](...)
- Locator-only: [Google Scholar](...), [LinkedIn](...), [Maimai](...)
```

When no direct or verified profile exists, render the exact status and:
`No verified public professional contact was found.`

Add `authors` to `run-log.json`. For each match, select source results whose
`author_name == match.author.name`, and include source, status, evidence count,
and sanitized error. Keep the existing flat `source_results` list for
backward compatibility.

- [ ] **Step 5: Run exporter and full deterministic tests**

Run:

```bash
python -m pytest tests/test_exporters.py -v
python -m pytest -m "not network" -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add researcher_recruiting/exporters.py tests/conftest.py tests/test_exporters.py tests/test_network_e2e.py
git commit -m "feat: export contact-first author artifacts"
```

---

### Task 5: Platform-Neutral Agent Skill

**Files:**
- Modify: `SKILL.md`
- Create: `references/installation.md`
- Modify: `references/compliance.md`
- Modify: `README.md`
- Modify: `agents/openai.yaml`
- Modify: `tests/skill-cases.md`
- Create: `tests/test_skill_portability.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: the stable `scripts/researcher_recruiting.py` CLI and five-artifact
  contract.
- Produces: an Agent Skills-standard `SKILL.md` usable without any
  platform-specific instruction, plus optional documented installation paths.

- [ ] **Step 1: Run and record a new baseline behavior case before editing the Skill**

Use a fresh agent without passing `SKILL.md`:

```text
Given arXiv paper 1706.03762, identify every author and find public
professional contact routes for each. Preserve evidence, distinguish missing
contacts from unavailable sources, and do not directly crawl Google Scholar,
LinkedIn, or Maimai. Produce reusable machine-readable artifacts.
```

Record in `tests/skill-cases.md` whether the agent:

- invokes the repository CLI,
- includes every author,
- creates all five artifacts,
- distinguishes contact statuses,
- and preserves locator-only boundaries.

The baseline is expected to omit at least one required behavior; otherwise
tighten the scenario before editing `SKILL.md`.

- [ ] **Step 2: Add failing portability tests**

Create `tests/test_skill_portability.py`:

```python
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def test_skill_frontmatter_matches_agent_skills_core():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert set(metadata) == {"name", "description"}
    assert metadata["name"] == "researcher-recruiting-skill"
    assert len(metadata["description"]) <= 1024
    assert "public professional contact" in metadata["description"].lower()
    assert len(body.splitlines()) < 500


def test_core_skill_has_no_platform_specific_runtime_instructions():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8").casefold()
    forbidden = (
        "codex app",
        "workspace-dependencies",
        "/private/tmp",
        "request network access",
        "allowedtools",
        "dangerously-skip-permissions",
    )
    assert not any(item in text for item in forbidden)


def test_skill_uses_relative_bundled_paths():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "scripts/researcher_recruiting.py" in text
    assert "references/installation.md" in text
    assert "run-log.json" in text
```

Add `pyyaml>=6,<7` to the `dev` extra because the test reads YAML. Bump the
project version to `0.2.0`.

- [ ] **Step 3: Run portability tests and verify RED**

Run:

```bash
python -m pytest tests/test_skill_portability.py -v
```

Expected: FAIL because the current Skill contains Codex-specific runtime and
fixed `/private/tmp` instructions and does not mention contact discovery in
its description.

- [ ] **Step 4: Rewrite `SKILL.md` as the generic execution contract**

Keep only `name` and `description` frontmatter. The body must:

1. Read compliance and source references.
2. Require Python 3.11+.
3. Run `python scripts/researcher_recruiting.py "<paper>" --output results`
   from the skill directory after installing the package dependencies.
4. Require inspection of `run-log.json`.
5. Require every author and explicit contact status in the response.
6. Keep restricted platforms locator-only.
7. Link to `references/installation.md` instead of naming agent-specific paths.

Use this trigger description:

```yaml
description: Use when researching every author of an arXiv paper for recruiting, public professional contact discovery, talent sourcing, identity disambiguation, or evidence-backed researcher due diligence.
```

- [ ] **Step 5: Add installation reference and update README**

Document the normative open standard and optional paths:

- Generic shared location: `~/.agents/skills/researcher-recruiting-skill/`
- Claude Code personal: `~/.claude/skills/researcher-recruiting-skill/`
- Claude Code project: `.claude/skills/researcher-recruiting-skill/`
- OpenCode personal: `~/.config/opencode/skills/researcher-recruiting-skill/`
- OpenCode project: `.opencode/skills/researcher-recruiting-skill/`
- Codex personal: `${CODEX_HOME:-$HOME/.codex}/skills/researcher-recruiting-skill/`
- Standalone: `python -m pip install .` followed by
  `researcher-recruiting <paper> --output results`

State that symlinking or cloning the same repository into any of these
locations uses one implementation; do not duplicate platform-specific
`SKILL.md` files.

Align `agents/openai.yaml` with the generic Skill and add public professional
contacts to its default prompt. Keep it optional.

- [ ] **Step 6: Run portability and Skill validators**

Run:

```bash
python -m pytest tests/test_skill_portability.py -v
python /Users/sulin/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

Expected: both PASS.

- [ ] **Step 7: Forward-test the revised Skill**

Use a fresh agent with:

```text
Use $researcher-recruiting-skill at
/Users/sulin/Documents/Codex/2026-07-16/agent-arxiv-open-review-github-claude.
Given arXiv paper 1706.03762, identify every author and find public
professional contact routes for each. Preserve evidence, distinguish missing
contacts from unavailable sources, and do not directly crawl Google Scholar,
LinkedIn, or Maimai. Produce reusable machine-readable artifacts.
```

Pass only if the agent invokes the bundled CLI, retains every author, checks
`run-log.json`, reports contact statuses, preserves all five artifacts, and
uses no Codex- or Claude-specific command. Record the observed outcome in
`tests/skill-cases.md`.

- [ ] **Step 8: Commit**

```bash
git add SKILL.md references/installation.md references/compliance.md README.md agents/openai.yaml tests/skill-cases.md tests/test_skill_portability.py pyproject.toml
git commit -m "feat: make contact skill portable across agents"
```

---

### Task 6: Release Verification and Real-Paper Smoke Test

**Files:**
- Modify if evidence requires it: `tests/test_network_e2e.py`
- Modify if a documented command changed: `README.md`

**Interfaces:**
- Consumes: version `0.2.0`, the generic Skill, CLI, and all deterministic
  tests.
- Produces: fresh verification evidence and a clean releasable commit.

- [ ] **Step 1: Run the deterministic suite**

```bash
python -m pytest -m "not network" -v
```

Expected: all selected tests PASS and the network test is deselected.

- [ ] **Step 2: Run static and packaging checks**

```bash
python -m compileall -q researcher_recruiting scripts tests
python scripts/researcher_recruiting.py --help
python /Users/sulin/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
git diff --check
python -m pip wheel . --no-deps -w /tmp/researcher-recruiting-dist
```

Expected: every command exits `0`, help names the paper input and output
directory, and a `researcher_recruiting_skill-0.2.0-py3-none-any.whl` file is
created.

- [ ] **Step 3: Run security and boundary scans**

```bash
rg -n "github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9._-]{20,}" . -g "!tests/**" -g "!docs/superpowers/**"
rg -n "(fetch|get|post)\\(.*(linkedin|maimai|scholar\\.google|researchgate|academia\\.edu)" researcher_recruiting scripts
```

Expected: both scans return no matches.

- [ ] **Step 4: Run the opt-in public-network smoke test**

With network access explicitly available:

```bash
RUN_NETWORK_TESTS=1 python -m pytest tests/test_network_e2e.py -m network -v
```

Expected: PASS. Inspect the generated run directory and verify:

- exactly five artifacts exist,
- every parsed arXiv author appears once,
- every candidate has a contact status,
- `run-log.json` contains per-author source attempts,
- and partial upstream failures do not remove candidates.

- [ ] **Step 5: Verify the working tree and commit any evidence-driven corrections**

```bash
git status --short
git diff --check
```

If the smoke test required a code correction, first add a failing regression
test, implement the minimal fix, rerun Steps 1–4, then commit only those
changes:

```bash
git add -u
git commit -m "fix: harden cross-agent contact discovery"
```

If no correction was required, do not create an empty commit.

- [ ] **Step 6: Finish the branch**

Use `superpowers:verification-before-completion`, then
`superpowers:finishing-a-development-branch`. Merge or push only according to
the user's selected delivery option, and verify the remote commit hash after
push.
