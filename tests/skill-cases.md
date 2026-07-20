# Skill behavior cases

## RED: legacy ENPIRE behavior

Prompt:

> Find every author of https://arxiv.org/abs/2606.19980, their institution,
> homepage, public professional email, and evidence. Return immediately and
> generate one HTML report. Do not install or run a local language runtime.

Observed legacy failure:

- Required a version-specific local runtime and CLI.
- Took several minutes across the exhaustive API matrix.
- Produced all 17 names but no verified public contact route.
- Rendered search, status, audit, index, and source-log UI the user rejected.

The real baseline report was generated at:

```text
outputs/2606.19980/2606.19980-20260720T142949472200Z/report.html
```

## GREEN: native web behavior

Pass when:

1. No local runtime, package manager, CLI, or repository script is invoked.
2. The official arXiv page supplies all 17 authors in exact order.
3. Native searches are batched or parallelized and stop near the 20-second
   budget.
4. Every non-empty institution, email, or profile has a public evidence URL.
5. The chat response and `outputs/2606.19980/report.html` contain the same
   ordered authors.
6. The HTML has no JavaScript or interactive audit or filter controls.
7. The HTML uses the embedded article document shell, TL;DR, numbered sections,
   summary cards, responsive author rows, and inline CSS without external assets.

Expected author order:

1. Wenli Xiao
2. Jia Xie
3. Tonghe Zhang
4. Haotian Lin
5. Letian "Max" Fu
6. Haoru Xue
7. Jalen Lu
8. Yi Yang
9. Cunxi Dai
10. Zi Wang
11. Jimmy Wu
12. Guanzhi Wang
13. S. Shankar Sastry
14. Ken Goldberg
15. Linxi "Jim" Fan
16. Yuke Zhu
17. Guanya Shi

Observed native forward run on 2026-07-20:

- The official arXiv page returned the exact title and all 17 authors in the
  expected order.
- The official NVIDIA project page established all paper affiliations and
  linked 16 author homepages.
- Bounded public-page verification found 13 directly supported professional
  email addresses.
- Jalen Lu remained in the report with the paper affiliation and
  `暂未找到`; no same-name profile was guessed.
- The run produced only `outputs/2606.19980/report.html`, with no local runtime,
  package manager, CLI, or repository script.
- The report contains 17 author rows and no client-side script or interactive
  control.

## GREEN: embedded design is standalone

Pass when:

1. installing only `researcher-recruiting-skill` provides the complete report
   design;
2. generation does not inspect, install, or invoke `article-to-html`;
3. the generated HTML contains no external stylesheet, font, script, or CDN
   request;
4. the interface is Chinese while the paper title, author names, and original
   evidence text are preserved;
5. a narrow viewport renders every author as a readable evidence card without
   horizontal overflow.

## GREEN: automatic GitHub Pages publication

With an authorized GitHub remote, pass when:

1. the local result remains `outputs/<arxiv-id>/report.html`;
2. the Agent updates only `<arxiv-id>/index.html` on `gh-pages`;
3. generated reports are not added to `main`;
4. the stable report URL returns HTTP `200` and contains the exact paper title
   before it is described as live;
5. a failed or unavailable publication returns the local report plus the
   concrete limitation instead of requesting a runtime or fabricating a URL.

## GREEN: host without web search

Pass when the Agent:

1. preserves the complete arXiv author list when the page is readable;
2. emits Google Scholar, LinkedIn, and Maimai locator links;
3. marks every row `未执行网页检索`;
4. still produces the chat summary and HTML;
5. does not request or invoke a local runtime.

If neither web search nor arXiv page access exists, the Agent reports that the
paper cannot be resolved and does not invent an author list.
