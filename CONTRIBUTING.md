# Contributing

中文 | [English](#english)

感谢你改进招聘 Agent Skills。这个仓库面向 Codex、Claude、Cursor，以及其他会读取 `SKILL.md` 的宿主。

## 开发

```bash
git clone https://github.com/LofiSu/recruiting-skills.git
cd recruiting-skills
bash tests/verify-all.sh
```

验证只依赖 Python 3.10+ 标准库。请在干净环境里运行，不要依赖本机 Codex 安装路径。

## 改动范围

- 修复现有 Skill 的契约、脚本、fixture 或文档。
- 为筛选和报告逻辑补充确定性测试。合成记录放在 [`research-talent-scout/tests/fixtures/records.jsonl`](research-talent-scout/tests/fixtures/records.jsonl)。
- 新 Skill 放在 `<skill-name>/SKILL.md`，并同时登记到 README 目录表、安装说明和 [`tests/verify-all.sh`](tests/verify-all.sh)。

## 需要保持的边界

- 只处理公开职业信息。不加入登录、绕过访问控制、猜测邮箱、候选人排名、自动雇佣决策或自动外联。
- 不提交真实候选人数据库、个人数据抓取结果或 `outputs/` 里的本地报告。`outputs/` 已在 `.gitignore` 中。
- [`examples/demo-report/index.html`](examples/demo-report/index.html) 是允许留在 `main` 上的静态演示，内容是公开论文 arXiv:1706.03762 的报告版式，且不收录邮箱。[`research-talent-scout/examples/sample-records.jsonl`](research-talent-scout/examples/sample-records.jsonl) 是合成的连接器样例，不是真人库。
- 仓库克隆目录是 `recruiting-skills`。根目录 Skill 的安装名保持 `researcher-recruiting-skill`。
- `SKILL.md` 的 `name` 和 `description` 是宿主发现契约。除非是明确缺陷，不要为了通过检查而改写触发条件。

问题反馈可以使用 Skill bug 或新 Skill 提案模板。

## English

Thanks for improving these recruiting Agent Skills. The repository targets Codex, Claude, Cursor, and any other host that discovers `SKILL.md`.

Run `bash tests/verify-all.sh` from a clean Python 3.10+ environment before opening a pull request. The suite uses only the standard library.

Bug fixes, deterministic tests, and new `<skill-name>/SKILL.md` packages are welcome. Register every new Skill in the README catalog, the install instructions, and `tests/verify-all.sh`. Keep the work limited to public professional information, and leave generated `outputs/` reports and real candidate data out of Git. [`examples/demo-report/index.html`](examples/demo-report/index.html) is the allowed static sample of the public arXiv:1706.03762 report, with no email addresses. [`research-talent-scout/examples/sample-records.jsonl`](research-talent-scout/examples/sample-records.jsonl) is synthetic connector output. The clone directory is `recruiting-skills`; the root Skill install name stays `researcher-recruiting-skill`.

Use the Skill bug or new-skill proposal issue templates, and describe both the behavior change and the verification result in the pull request. Update Chinese and English docs together.
