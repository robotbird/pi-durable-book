---
name: pi-durable-book-sync
description: 将 pi-durable 中文手册（robotbird/pi-durable-book）同步到上游 @earendil-works/pi 的最新发布版本。当用户提到"检查/扫描 pi-durable 新版本"、"更新书/手册到 vX.Y.Z"、"上游发了新版本"、"同步 book 内容"或询问 pi-durable 版本变化时使用——即使没有明说"book"，只要上下文涉及 pi-durable 版本更新与中文手册，就应触发。
---

# pi-durable 中文手册上游同步

把 `/Users/robotbird/Works/yepeng/pibook/pidurable`（本地工作区，远程 `robotbird/pi-durable-book`）更新到上游 `@earendil-works/pi` `packages/durable` 的最新发布版本。书结构：`book/01-概述与快速上手.md`（←README）、`book/02-规范说明书/01..06-*.md`（←docs/spec.md 六节）、`book/03-设计文档/*.md`（←docs/ 其他文档，可能被上游删除）、`book/04-示例教程/*.md`（←test/examples/ 32 个示例）。

## 流程

### 1. 确认新版本与当前基线

```bash
npm view @earendil-works/pi-durable dist-tags time.modified
grep -m1 "全书内容基于" <workspace>/README.md   # 书的当前基线
```

npm 网络查询可能挂起：加 timeout，必要时转后台，超 60s 就放弃 npm 改从 GitHub tags 判断。

### 2. 拉取版本（新 tag 与书基线 tag 各一份）

```bash
git clone --depth 1 --branch <tag> --filter=blob:none --sparse https://github.com/earendil-works/pi /tmp/pi-<tag短名>
cd /tmp/pi-<tag短名> && git sparse-checkout set packages/durable
```

- **不要用 curl 下 GitHub tarball**——本会话两次遇到 HTTP/2 截断（exit 16 / truncated gzip），sparse clone 稳定。
- 需要对比 main 未发布内容时：`git fetch --depth 1 origin main`，然后 `git archive FETCH_HEAD packages/durable | tar -x -C <dir>`（sparse clone 无 origin/main 引用，用 FETCH_HEAD）。
- macOS 会清理数日前的 /tmp：发现旧 checkout 残缺（`not a git repository`）直接重新 clone。

### 3. 差异分析 → 影响映射

```bash
diff -rq /tmp/pi-old/packages/durable /tmp/pi-new/packages/durable
diff old/README.md new/README.md > /tmp/readme.diff      # 逐块看
diff old/docs/spec.md new/docs/spec.md > /tmp/spec.diff  # 用 grep '^[0-9]' 列 hunk
grep -n "^## " new/docs/spec.md                          # 新版章节行号（引用块要用）
```

映射规则：README diff→第一篇；spec hunk 按章节→第二篇对应文件；`test/examples/*.ts`→第四篇对应文章（常只有一两行 API 改名，如 `content`→`output`）；docs/ 设计文档**被删除**→第三篇存档化（见第 5 步）。先读 `CHANGELOG.md` 顶部新版本段理解语义，再动手。

### 4. 派发并行更新（每次最多 3 个 agent，多了会撞并发上限）

每个 agent 的提示词模板见 [references/agent-prompts.md](references/agent-prompts.md)。要点：给足两版原文路径 + diff 文件路径 + 该节新旧行号区间；要求 Read 后 **Edit 逐处改、禁止整文件重写**；未受影响段落不动。

### 5. 特殊处理

- **上游删除的文档**（如 v1.2.0 删了 3 篇设计文档）：译文保留，引用块链接改为最后一个包含它的 tag：`https://github.com/earendil-works/pi/blob/<tag>/packages/durable/docs/...`，并加一行 `> ⚠️ 上游已在 vX.Y.Z 中移除此文档；本篇为存档翻译`。导读 README 的篇章表和 SUMMARY.md 同步标注"（存档）"。
- **spec/README 章节改名**（如 Pico5→Durable）：全书 grep 旧名，同步 SUMMARY、导读、第一篇中的交叉引用。

### 6. 版本标注（收尾必做）

- 六个 spec 引用块：`（v<new>）第 A–B 行`，A/B 按新版 `^## ` 行号边界。
- `<workspace>/README.md` 基线行、`book/01-概述与快速上手.md` 引用块。
- `grep -rn "v<old>）第\|基于 \*\*v<old>"` 确认无残留（第三篇存档链接除外）。

### 7. 校验、提交、推送

```bash
python3 <skill目录>/scripts/validate_links.py   # 相对链接 0 失效
git add -A && git commit -m "全书更新至 vX.Y.Z：<一句话要点列表>" && git push origin main
```

提交信息风格：`全书更新至 v1.2.0：嵌套工具调用、结构化输出、…；第三篇设计文档存档化（上游已移除）`。

### 8. 可选：X 发布帖

写到 `/Users/robotbird/Downloads/pi-durable-vX.Y.Z-X发布帖.md`：完整单帖版（用户是 Premium，不限字符）+ 备选精简版；结构：一句话定位 → 新能力逐条（emoji 编号）→ ⚠️ 破坏性变更 → 文档/手册链接 + `#AIAgents #OpenSource #LLM`。手册同步完成后才能写"已同步"。

## 陷阱清单（本会话实测）

1. 批量脚本改过的文件，Edit 前必须重新 Read（"File has been modified since read"）。
2. agent 派发 8 个会失败（`user concurrency limit exceeded` / `exceed quota limit`），3 个一批最稳；失败的重发即可。
3. 示例文章的代码块必须与源文件**逐字一致**（含 tab），更新后用脚本做"逐字包含"比对。
4. 引用块行号是**原文行号**，六节范围用新版 `^## ` 边界推导，改版后必然整体偏移，别漏。
