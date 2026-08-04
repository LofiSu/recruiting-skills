#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


def _escape(value) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def _render_section(title: str, rows: list) -> list:
    lines = [f"## {title}", ""]
    if not rows:
        lines.extend(["暂无匹配候选人。", ""])
        return lines
    lines.extend([
        "| 姓名 | 学位 | 院校/实验室 | 毕业 | 符合数量 | 分类统计 | 最近核验 |",
        "|---|---|---|---:|---:|---|---|",
    ])
    for row in rows:
        counts = ", ".join(
            f"{category}={count}"
            for category, count in row.get("counts_by_category", {}).items()
            if count
        ) or "—"
        affiliation = " / ".join(filter(None, [row.get("institution"), row.get("lab")]))
        lines.append(
            "| {name} | {degree} | {affiliation} | {year} ({state}) | {count} | {counts} | {verified} |".format(
                name=_escape(row.get("name")), degree=_escape(row.get("degree")),
                affiliation=_escape(affiliation), year=_escape(row.get("graduation_year")),
                state=_escape(row.get("graduation_state")), count=row.get("qualifying_count", 0),
                counts=_escape(counts), verified=_escape(row.get("verified_at")),
            )
        )
    lines.append("")
    for row in rows:
        lines.extend(["", f"**{_escape(row.get('name'))} 的符合论文**", ""])
        for paper in row.get("qualifying_publications", []):
            label = _escape(paper.get("title"))
            url = paper.get("url", "")
            linked = f"[{label}]({url})" if url.startswith(("https://", "http://")) else label
            lines.append(
                f"- {linked} — {_escape(paper.get('normalized_venue'))} {paper.get('year')} · `{_escape(paper.get('category'))}`"
            )
        lines.extend(["", "毕业与身份证据：", ""])
        for evidence in row.get("evidence", []):
            excerpt = _escape(evidence.get("excerpt")) or _escape(evidence.get("field"))
            url = evidence.get("url", "")
            linked = f"[{excerpt}]({url})" if url.startswith(("https://", "http://")) else excerpt
            lines.append(
                f"- {linked} — `{_escape(evidence.get('state'))}`，核验于 {_escape(evidence.get('retrieved_at'))}"
            )
        lines.append("")
    return lines


def render_markdown(result: dict) -> str:
    lines = ["# 研究人才候选结果", "", f"生成时间：{_escape(result.get('generated_at'))}", ""]
    lines.extend(_render_section("已确认", result.get("confirmed", [])))
    lines.extend(_render_section("高概率待确认", result.get("likely_needs_verification", [])))
    lines.extend(["## 索引覆盖", ""])
    coverage = result.get("coverage", [])
    if coverage:
        for item in coverage:
            lines.append(
                f"- {_escape(item.get('scope'))}：最近核验 {_escape(item.get('last_verified_at'))}"
                + (f"；缺口：{_escape(item.get('gaps'))}" if item.get("gaps") else "")
            )
    else:
        lines.append("- 暂无覆盖元数据；空结果不代表不存在符合条件的人。")
    lines.extend(["", "## 警告与边界", ""])
    warnings = result.get("warnings", [])
    lines.extend(f"- {_escape(warning)}" for warning in warnings)
    if not warnings:
        lines.append("- 无额外警告。")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render researcher query JSON as Markdown")
    parser.add_argument("--input", default="-")
    args = parser.parse_args()
    if args.input == "-":
        result = json.load(sys.stdin)
    else:
        result = json.loads(Path(args.input).read_text(encoding="utf-8"))
    sys.stdout.write(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
