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

## GREEN: host without web search

Pass when the Agent:

1. preserves the complete arXiv author list when the page is readable;
2. emits Google Scholar, LinkedIn, and Maimai locator links;
3. marks every row `未执行网页检索`;
4. still produces the chat summary and HTML;
5. does not request or invoke a local runtime.

If neither web search nor arXiv page access exists, the Agent reports that the
paper cannot be resolved and does not invent an author list.
