# 翻译更新 Agent 提示词模板

按书的四个部分套用。公共风格约束（写进每个提示词）：意译为主、术语首现中英对照；类型名/API 名/代码块保持英文原样**一字不改**；用 Read 读文件、Edit 逐处修改，**禁止整文件重写**；未受影响段落一律不动；完成后回复修改处数。

## 第一篇（README 全译）

```
把中文译文更新到 <new_tag>。译文：<workspace>/book/01-概述与快速上手.md（当前基于 <old_tag>）。

参考资料：
- <old_tag> 原文：/tmp/pi-<old>/packages/durable/README.md
- <new_tag> 原文：/tmp/pi-<new>/packages/durable/README.md
- 完整 diff：/tmp/readme.diff

任务：
1. 先读 diff 和两版原文，理解每处变化的语义。
2. 逐处更新译文对应段落：新内容按译文风格意译补入，删除的移除，改写的对应改写；新增章节插入对应标题，保持与 <new_tag> README 章节结构一致。
3. 开头引用块版本标注改为 <new_tag>。
```

## 第二篇（spec 六节，每节一个 agent）

```
把 Pico5/Durable 规范中文译文从 <old_tag> 更新到 <new_tag>。

文件：<workspace>/book/02-规范说明书/<NN>-<节名>.md（当前基于 <old_tag>，覆盖 spec §X-Y，旧版第 A–B 行区域）。

参考资料：
- 旧版原文：/tmp/pi-<old>/packages/durable/docs/spec.md（§X 从 A1 行起…）
- 新版原文：/tmp/pi-<new>/packages/durable/docs/spec.md（§X 从 B1 行起…）
- 完整 diff：/tmp/spec-120.diff（你只关心落在本节区间的 hunk，旧版行号 A–B）

任务：
1. 筛出落在本节范围的 hunk，对照两版原文理解语义（先读 CHANGELOG 新版本段）。
2. 逐处更新译文；注意可能新增小节（如 §7.6、§10.1），标题层级同步。
3. 开头引用块改为：「（<new_tag>）第 <新A>–<新B> 行」（用新版 ^## 边界）。
```

六节行号边界获取：`grep -n "^## " /tmp/pi-<new>/packages/durable/docs/spec.md`，节 N 的范围 = 本节 `^##` 行 − 1 到下节 `^##` 行 − 1（末节到文件尾）。

## 第三篇（设计文档，仅当原文变化或被删除时）

变化：同第一篇模板但指向对应 docs/*.md。
被删除：不派 agent，手工处理——引用块链接改到最后一个包含该文件的 tag：`https://github.com/earendil-works/pi/blob/<last_tag>/packages/durable/docs/<file>`，引用块后加：
`> ⚠️ 上游已在 <new_tag> 中移除此文档；本篇为 <last_tag> 及之前版本的存档翻译，链接指向历史版本。`
并更新导读 README 篇章表加"（存档）"、SUMMARY.md 篇标题加"（存档，上游 <new_tag> 已移除原文）"。

## 第四篇（示例教程）

```
把 N 篇示例教程文章从 <old_tag> 更新到 <new_tag>。源代码两份：
- 旧：/tmp/pi-<old>/packages/durable/test/examples/
- 新：/tmp/pi-<new>/packages/durable/test/examples/

变化的示例与文章一一对应（先 diff -rq 找出变化的示例文件）。

任务：
1. 对每个示例 diff 两版源文件，理解变化（常见：单个 API 改名如 content→output）。
2. 更新文章中受影响的代码块，使其与新源文件逐字一致（含 tab 缩进）；受影响的中文讲解同步改写；「本例演示」「关键点」受影响才改。
3. 验证：文章中全部 ```ts 代码块与新源文件做逐字包含比对，全部匹配；grep 确认无旧 API 写法残留。
```
