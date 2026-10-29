# Repository metadata

GitHub topics and the About description are repository settings. Putting them in git does not publish them. Apply the values below in GitHub → About.

## Suggested description

```text
Agent Skills for researcher recruiting: arXiv author enrichment + cohort talent scout with evidence-backed reports.
```

## Suggested topics

```text
agent-skills
recruiting
arxiv
codex
claude
talent-scout
research
python
```

## Discovery notes

- Agent index: [`llms.txt`](llms.txt) lists the short project summary and the key paths (`SKILL.md`, `research-talent-scout/`, `examples/demo-report/`, this file).
- Clone URL: `https://github.com/LofiSu/recruiting-skills.git`
- Root Skill install name: `researcher-recruiting-skill` (the `name` in the root `SKILL.md`)
- Second Skill install name: `research-talent-scout`
- Hosts: Codex (`${CODEX_HOME:-~/.codex}/skills`), Claude Code (`~/.claude/skills` or `.claude/skills`), Cursor (`~/.cursor/skills`, `~/.agents/skills`, or the matching project directories). Cursor also reads the Codex and Claude directories.
- The repository includes the SQLite index engine, synthetic fixtures at `research-talent-scout/tests/fixtures/records.jsonl`, OpenAlex and Semantic Scholar connectors, and a static demo report at `examples/demo-report/index.html`. It does not include a live candidate database.
- License: MIT
