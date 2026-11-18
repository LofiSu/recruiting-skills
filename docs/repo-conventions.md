# 仓库约定 · Repository Conventions

中文 | [English](#english)

## 基本约定

- 克隆目录是 `recruiting-skills`。根目录 Skill 的安装名仍是 `researcher-recruiting-skill`，以兼容现有触发方式。
- 其他招聘 Skill 使用独立的 `<skill-name>/SKILL.md` 子目录。
- 每个 Skill 可以独立安装、触发和验证。
- 跨 Skill 协作必须定义稳定输入、输出、责任边界和失败降级。
- 通用合规原则保持一致：只处理公开职业信息，不执行招聘排名、自动雇佣决策或自动外联。

## 新增 Skill

新增 Skill 后，需要在以下位置登记：

1. README 顶部目录表（两种语言）
2. README 安装说明（两种语言）
3. `tests/verify-all.sh` 统一验证脚本

发现用的仓库简介和 GitHub topics 写在 [`REPO_META.md`](../REPO_META.md)；这些设置不能靠 git 文件自动生效，必须在 GitHub → About 里手工套用。

2026-10-29 的对照（可安装 `SKILL.md`、演示报告、双语 README、topics、MIT、CI，以及当时尚未套用的 topics）见 [`docs/trending-notes-2026-10-29.md`](trending-notes-2026-10-29.md)。

---

## English

## Basic conventions

- Clone the repository as `recruiting-skills`. The root Skill install name remains `researcher-recruiting-skill` so existing triggers keep working.
- Additional recruiting Skills live in independent `<skill-name>/SKILL.md` directories.
- Every Skill must remain independently installable, triggerable, and verifiable.
- Cross-Skill workflows must define stable inputs, outputs, ownership, and failure behavior.
- Shared compliance rules permit only public professional information and prohibit candidate ranking, automated employment decisions, and automated outreach.

## Adding a new Skill

Register every new Skill in:

1. The catalog table at the top of README (both languages)
2. The installation section of README (both languages)
3. `tests/verify-all.sh`

The suggested GitHub About description and topics live in [`REPO_META.md`](../REPO_META.md). Committing a file does not publish those settings; apply them in GitHub → About by hand.

The 2026-10-29 snapshot (installable `SKILL.md`, demo report, bilingual README, topics, MIT license, CI — including topics that were still unset on that date) is [`docs/trending-notes-2026-10-29.md`](trending-notes-2026-10-29.md).
