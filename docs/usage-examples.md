# 使用示例 · Usage Examples

中文 | [English](#english)

## 调查一篇论文的全部作者

向宿主发送论文 URL、arXiv ID 或精确标题。自然语言请求会自动触发 `researcher-recruiting-skill`，也可以显式调用：

```text
https://arxiv.org/abs/2606.19980
帮我找这篇论文所有作者的机构、主页、公开职业邮箱和证据链接。
```

显式调用：

```text
Use $researcher-recruiting-skill on https://arxiv.org/abs/2606.19980.
Find every author's institution, homepage, public professional email,
GitHub/OpenReview profile, and evidence.
```

## 批量筛选研究人才

```text
Use $research-talent-scout to find indexed 2027 and 2028 graduates.
For PhD candidates require more than 5 qualifying papers; for master's
candidates require more than 3. Count ACL, ICML, ICLR, NeurIPS, EMNLP,
CVPR, AAAI, ICCV, MLSys, OSDI, EuroSys, ASPLOS, ISCA, SC, and PPoPP.
Separate confirmed graduation years from candidates needing verification,
then enrich only the qualifying candidates with public professional evidence.
```

"全部候选人"表示当前索引覆盖范围内的全部匹配者，不代表从实时互联网穷举全球所有研究者。

---

## English

## Paper author investigation

Send the paper URL, arXiv ID, or exact title to the host. Natural-language requests trigger `researcher-recruiting-skill` automatically; explicit call:

```text
Use $researcher-recruiting-skill on https://arxiv.org/abs/2606.19980.
Find every author's institution, homepage, public professional email,
GitHub/OpenReview profile, and evidence.
```

## Cohort talent scouting

```text
Use $research-talent-scout to find indexed 2027 and 2028 graduates.
For PhD candidates require more than 5 qualifying papers; for master's
candidates require more than 3. Count ACL, ICML, ICLR, NeurIPS, EMNLP,
CVPR, AAAI, ICCV, MLSys, OSDI, EuroSys, ASPLOS, ISCA, SC, and PPoPP.
Separate confirmed graduation years from candidates needing verification,
then enrich only the qualifying candidates with public professional evidence.
```

"All candidates" means all matches within the current index coverage — not an exhaustive live-web census of every researcher.
