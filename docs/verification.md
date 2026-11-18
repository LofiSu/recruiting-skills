# 验证 · Verification

中文 | [English](#english)

从仓库根目录运行：

```bash
bash tests/verify-all.sh
```

它会验证论文作者 Skill 的静态契约、两个 Skill 的 frontmatter、Pages 首页生成器、演示报告，以及 `research-talent-scout` 的索引、导入、查询、连接器映射和报告测试。连接器测试使用仓库里的 HTTP fixture，不访问网络。GitHub Actions 在推送到 `main` 和指向 `main` 的 pull request 上运行同一命令。frontmatter 检查使用仓库内的标准库脚本（`scripts/validate_skill_frontmatter.py`），不依赖某台机器上的 skill-creator 路径。

---

## English

Run from the repository root:

```bash
bash tests/verify-all.sh
```

This validates both Skill structures, frontmatter, the original paper-mode contract, the Pages homepage generator, the demo report, and the scout's deterministic index, import, query, connector-mapping, evidence-state, and rendering tests. Connector tests use checked-in HTTP fixtures and do not touch the network. GitHub Actions runs the same command on pushes and pull requests to `main`. The frontmatter check uses the in-repo script `scripts/validate_skill_frontmatter.py` and does not depend on any machine-local path.
