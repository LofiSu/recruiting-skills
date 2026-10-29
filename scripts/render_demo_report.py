#!/usr/bin/env python3
"""Fill the paper-report template with a frozen public demo.

The sample is arXiv:1706.03762, Attention Is All You Need. Author order comes
from the arXiv API. Affiliations come from the paper HTML. Email addresses
printed in that HTML are omitted on purpose. Regenerate with:

    python3 scripts/render_demo_report.py
    python3 scripts/render_demo_report.py --check
"""

from __future__ import annotations

import argparse
import sys
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "assets" / "report-template.html"
DEFAULT_OUTPUT = ROOT / "examples" / "demo-report" / "index.html"

ARXIV_ID = "1706.03762"
ARXIV_ABS = "https://arxiv.org/abs/1706.03762"
ARXIV_HTML = "https://arxiv.org/html/1706.03762"
ARXIV_PDF = "https://arxiv.org/pdf/1706.03762"
GENERATED_AT = "2026-10-29"

AUTHORS = (
    ("Ashish Vaswani", "Google Brain"),
    ("Noam Shazeer", "Google Brain"),
    ("Niki Parmar", "Google Research"),
    ("Jakob Uszkoreit", "Google Research"),
    ("Llion Jones", "Google Research"),
    ("Aidan N. Gomez", "University of Toronto"),
    ("Lukasz Kaiser", "Google Brain"),
    ("Illia Polosukhin", "Google Research"),
)


def render_demo_report() -> str:
    """Return the demo report HTML. Tokens in the template are all replaced."""
    template = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "{{ARXIV_ID}}": escape(ARXIV_ID),
        "{{PAPER_TITLE}}": escape("Attention Is All You Need"),
        "{{ARXIV_URL}}": escape(ARXIV_ABS, quote=True),
        "{{GENERATED_AT}}": escape(GENERATED_AT),
        "{{PAPER_META}}": (
            '<span>演示样本 · DEMO</span>'
            '<span>冻结日期 · 2026-10-29</span>'
            "<span>版本 · v7</span>"
        ),
        "{{TLDR_BODY}}": _tldr(),
        "{{OVERVIEW_BODY}}": _overview(),
        "{{AUTHOR_ROWS}}": "\n".join(_author_row(index, name, institution) for index, (name, institution) in enumerate(AUTHORS, 1)),
        "{{LIMITATIONS_BODY}}": _limitations(),
        "{{REFERENCE_ITEMS}}": _references(),
    }
    rendered = template
    for token, value in replacements.items():
        if token not in rendered:
            raise ValueError(f"missing template token {token}")
        rendered = rendered.replace(token, value)
    if "{{" in rendered:
        raise ValueError("unreplaced template token")
    return rendered


def write_demo_report(path: Path = DEFAULT_OUTPUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_demo_report(), encoding="utf-8")
    return path


def _author_row(index: int, name: str, institution: str) -> str:
    evidence = (
        f'<a href="{escape(ARXIV_HTML, quote=True)}" rel="noreferrer noopener">论文 HTML 中的 Affiliation</a>'
        f'<a href="{escape(ARXIV_ABS, quote=True)}" rel="noreferrer noopener">arXiv 摘要</a>'
    )
    return f"""<tr class="author-row">
                <th scope="row" data-label="作者">
                  <span class="author-name">{escape(name)}</span>
                  <span class="author-order">AUTHOR {index:02d}</span>
                </th>
                <td data-label="机构">{escape(institution)}</td>
                <td data-label="公开联系路径">
                  <div class="contact-list"><span class="muted">暂未找到</span></div>
                </td>
                <td data-label="状态">
                  <span class="state state-verified">已核验</span>
                </td>
                <td data-label="证据">
                  <div class="evidence-list">{evidence}</div>
                </td>
              </tr>"""


def _tldr() -> str:
    return (
        "<p>本页是报告版式的静态演示，不是一次新的联网检索。"
        "论文是 arXiv:1706.03762《Attention Is All You Need》。"
        "八位作者的姓名和顺序来自 arXiv API，机构来自论文 HTML 中写明的 Affiliation。"
        "公开联系路径一律标为暂未找到：演示故意不收录论文脚注里出现过的邮箱。</p>"
    )


def _overview() -> str:
    return (
        "<p>论文提出 Transformer：用注意力替代循环网络和卷积，做序列到序列的转换。"
        "作者在 WMT 2014 英德翻译上报告 28.4 BLEU，在英法翻译上报告单模型 41.8 BLEU，"
        "并在英语成分句法分析上做了补充实验。摘要与作者列表以 "
        f'<a href="{escape(ARXIV_ABS, quote=True)}" rel="noreferrer noopener">arXiv 官方记录</a> 为准。</p>'
        "<p>这里只把这篇公开论文当作 HTML 报告的样例，方便查看版式。"
        "论文脚注写明全体同等贡献，署名顺序是随机的，因此作者顺序不是贡献排序，也不能当成招聘排序。</p>"
    )


def _limitations() -> str:
    return (
        "<ul>"
        "<li>这是仓库内的演示样本，生成日期固定为 2026-10-29，对应当时读到的 arXiv 记录 1706.03762v7。</li>"
        "<li>机构是论文 HTML 上打印的隶属，反映的是论文所述关系，不是这些人的当前雇主。</li>"
        "<li>Aidan N. Gomez 的 Affiliation 是 University of Toronto，脚注写明工作完成于 Google Brain。</li>"
        "<li>Illia Polosukhin 的脚注写明工作完成于 Google Research。</li>"
        "<li>arXiv API 的作者名是 Lukasz Kaiser；论文 HTML 写作 Łukasz Kaiser。本报告采用 arXiv API 的姓名。</li>"
        "<li>论文 HTML 脚注含有历史邮箱。本演示不收录任何邮箱，也没有 mailto 链接。</li>"
        "<li>输出只供人工查看报告长什么样。不排名、不建议雇佣、不发起外联。</li>"
        "</ul>"
    )


def _references() -> str:
    items = (
        ("arXiv 摘要", ARXIV_ABS),
        ("论文 HTML", ARXIV_HTML),
        ("论文 PDF", ARXIV_PDF),
    )
    lines = []
    for label, url in items:
        lines.append(
            "<li>"
            f'<a href="{escape(url, quote=True)}" rel="noreferrer noopener">{escape(label)}</a>'
            f" · {escape(url)}"
            "</li>"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Exit 1 when the committed file differs")
    args = parser.parse_args(argv)
    rendered = render_demo_report()
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.is_file() else ""
        if current != rendered:
            print(f"demo report is out of date: {args.output}", file=sys.stderr)
            return 1
        print(args.output)
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
