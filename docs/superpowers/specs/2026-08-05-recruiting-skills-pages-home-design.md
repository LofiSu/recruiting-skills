# Recruiting Skills GitHub Pages 首页设计

## 目标

修复 `https://lofisu.github.io/recruiting-skills/` 根路径 404，并让首页长期作为招聘 Skills 的统一入口。首页以 Skill 安装和使用为主，以已发布的招聘报告列表为辅。

## 当前状态

- 仓库名已经是 `LofiSu/recruiting-skills`。
- `gh-pages` 分支存在，并包含 `.nojekyll`。
- 发布流程只写入 `<arxiv-id>/index.html`，没有根目录 `index.html`。
- 发布契约要求保留 `gh-pages` 上已经存在的其他报告。

## 方案

采用无构建依赖的静态首页：

1. 在 `main` 保存可复用的首页模板和索引生成脚本。
2. 生成器扫描发布目录中包含 `index.html` 的报告子目录。
3. 生成 `gh-pages/index.html`，但不修改或删除任何报告目录。
4. 更新发布说明，要求每次发布报告后运行首页生成器。
5. 首次上线时直接为现有 `gh-pages` 生成首页。

不采用 Jekyll 或前端框架，避免新增运行时和构建依赖。

## 页面内容

首页按以下顺序展示：

1. 仓库定位：招聘相关 Agent Skills 集合（Codex、Claude、Cursor 等宿主）。仓库名是 `LofiSu/recruiting-skills`。
2. 两个协作 Skill：
   - `researcher-recruiting-skill`：从论文出发发现作者、机构和公开职业联系渠道。
   - `research-talent-scout`：按毕业年份、学位和顶会一作数量筛选候选人，并保留证据等级。
3. 安装与调用示例，链接回 GitHub 仓库。
4. 已发布报告列表；没有报告时显示明确的空状态。

页面使用中文为主、英文名称为辅，并适配桌面与移动端。

## 组件边界

### 首页模板

负责固定文案、布局和视觉样式。模板只接受已经转义的报告列表 HTML，不访问网络，也不读取 Git 状态。

### 索引生成器

输入为一个 Pages 发布目录，输出为该目录的 `index.html`。它只把名称符合安全规则且包含 `index.html` 的直接子目录视为报告，并按名称排序。

生成器必须：

- 忽略隐藏目录和无首页的目录；
- 对显示文本和链接属性进行 HTML 转义；
- 使用相对链接，确保仓库改名或镜像后仍可工作；
- 不删除或改写报告文件。

### 发布说明

更新 `references/publishing.md` 中的 Git 和 GitHub API 流程，明确根首页是分支级文件，并要求报告发布完成后刷新索引。

## 数据流

```text
本地报告 HTML
  -> 写入 gh-pages/<arxiv-id>/index.html
  -> 扫描 gh-pages 下的报告目录
  -> 生成 gh-pages/index.html
  -> 提交并推送 gh-pages
```

## 错误处理

- 发布目录不存在时，生成器以非零状态退出并说明原因。
- 输出文件写入失败时，不继续提交。
- 单个无效目录被忽略，不影响其他报告进入列表。
- GitHub Pages 尚未启用时，保留现有提示：配置 `gh-pages / (root)`。

## 测试

使用 Python 标准库测试生成器，不增加第三方依赖。测试先失败再实现，覆盖：

1. 空发布目录能够生成包含两个 Skill 入口和空状态的首页。
2. 合法报告目录被转换为排序后的相对链接。
3. 隐藏目录、无 `index.html` 的目录和根文件不会进入列表。
4. 特殊字符被安全转义。
5. 现有 Skill 校验脚本继续通过。

## 成功标准

- `gh-pages/index.html` 存在。
- `https://lofisu.github.io/recruiting-skills/` 返回 HTTP 200。
- 页面包含两个 Skill 的安装入口。
- 已发布报告能够从首页打开。
- 后续报告发布会刷新列表且不会删除旧报告。
