# GitHub Pages 发布 · GitHub Pages Publishing

中文 | [English](#english)

单篇论文模式生成的报告不会写入 `main`。授权后，报告会发布至：

```text
branch: gh-pages
file:   <arxiv-id>/index.html
URL:    https://<owner>.github.io/<repository>/<arxiv-id>/
home:   https://<owner>.github.io/<repository>/
```

本仓库对应 `https://lofisu.github.io/recruiting-skills/`。首页由 [`scripts/build_pages_index.py`](../scripts/build_pages_index.py) 和 [`assets/pages-index-template.html`](../assets/pages-index-template.html) 生成。如果 GitHub 写入、Pages 设置或部署验证不可用，Skill 只返回本地报告，不会虚构线上地址。

想先看报告长什么样，打开 [`examples/demo-report/index.html`](../examples/demo-report/index.html)。那是提交在 `main` 上的静态样例，不是 `gh-pages` 上的一篇已发布报告。

---

## English

Paper-mode reports stay off `main`. When publication is authorized, the Skill publishes:

```text
branch: gh-pages
file:   <arxiv-id>/index.html
URL:    https://<owner>.github.io/<repository>/<arxiv-id>/
home:   https://<owner>.github.io/<repository>/
```

For this repository the collection home is `https://lofisu.github.io/recruiting-skills/`. [`scripts/build_pages_index.py`](../scripts/build_pages_index.py) renders it from [`assets/pages-index-template.html`](../assets/pages-index-template.html). If GitHub writes, Pages settings, or deployment checks are unavailable, the Skill returns the local report and does not invent a live URL.

To see the report layout before any Pages publish, open [`examples/demo-report/index.html`](../examples/demo-report/index.html). That file is a static sample committed on `main`, not a report published on `gh-pages`.
