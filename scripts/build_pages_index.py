#!/usr/bin/env python3
"""Build the static recruiting-skills GitHub Pages homepage."""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import re
import sys


REPORT_ID = re.compile(r"^[0-9]+(?:\.[0-9]+)+(?:v[0-9]+)?$")
TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "assets" / "pages-index-template.html"


def discover_reports(pages_dir: Path) -> list[str]:
    """Return sorted report IDs published as safe direct child directories."""
    return sorted(
        child.name
        for child in pages_dir.iterdir()
        if child.is_dir()
        and REPORT_ID.fullmatch(child.name)
        and (child / "index.html").is_file()
    )


def render_index(report_ids: list[str]) -> str:
    """Render the homepage with escaped relative links for report IDs."""
    if report_ids:
        report_list = "\n".join(
            '          <li><a href="{url}/">arXiv {label}</a></li>'.format(
                url=escape(report_id, quote=True),
                label=escape(report_id),
            )
            for report_id in report_ids
        )
        report_html = f'<ul class="report-list">\n{report_list}\n        </ul>'
    else:
        report_html = '<p class="empty">暂无已发布报告。运行论文作者调查后，报告会显示在这里。</p>'

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.replace("{{REPORT_LIST}}", report_html)


def write_index(pages_dir: Path) -> Path:
    """Write the root homepage without modifying any published report."""
    if not pages_dir.is_dir():
        raise NotADirectoryError(f"Pages directory does not exist: {pages_dir}")
    output = pages_dir / "index.html"
    output.write_text(render_index(discover_reports(pages_dir)), encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pages_directory", type=Path)
    args = parser.parse_args(argv)
    try:
        output = write_index(args.pages_directory)
    except (NotADirectoryError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
