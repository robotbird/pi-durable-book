# X.com 发布帖生成模板

为 pi-durable 版本更新生成 X 帖子时，按下述格式输出到 `/Users/robotbird/Downloads/pi-durable-vX.Y.Z-X发布帖.md`。用户是 X Premium（单帖不限字符），帖子由用户自行复制发布，**不要**代发。

## 文件结构

```markdown
# pi-durable vX.Y.Z · X.com 发布帖（Premium 长文单帖，直接复制发布）
---
<完整单帖版>
---
## 备选精简版
<短版>
```

## 完整单帖版结构（依次）

1. **开头一行**：emoji（🚀）+ 一句话点题，点出本版本的主题（如 v1.2.0 是"把工具调用做成一等公民"，v1.3.0 是小版本就直接列要点）。
2. **一句框架定位**（老读者可跳过的话）：pi-durable 是 earendil-works 开源的持久化智能体运行框架——对话、模型轮次、工具调用先落盘再展示，进程崩溃后从断点继续。
3. **新能力逐条**：emoji 数字（1️⃣2️⃣…）+ 小标题 + 2-4 句展开。每条给出：API 名（英文原样）、解决什么问题、值得记住的数字（性能数字最有传播力，如"11.3s → 1.4s"、"18.8s → 2.7s"、"内存 2.6 万文档 → 0"）。
4. **⚠️ 迁移注意（破坏性变更）**：逐条列出，写给需要升级的用户；无破坏性变更的小版本可省略此节或写"无破坏性变更"。
5. **文档/手册链接**：上游 `https://github.com/earendil-works/pi/tree/main/packages/durable`；手册 `https://github.com/robotbird/pi-durable-book`。
6. **话题标签**：`#AIAgents #OpenSource #TypeScript #LLM`，按内容可加 `#Cloudflare #AIInfra`。

## 备选精简版结构

5-6 行：emoji 数字列要点（每条一行、只留最抓人的短语）+ 链接 + 标签。发帖人想控制阅读负担时用。

## 风格规则

- 中文写作，API 名、错误码、配置键保持英文原样。
- 数字优先：版本变更里所有可量化的对比（耗时、内存、行数）都要落到具体数字。
- 破坏性变更必须如实、显式列出，放在可见位置——这是给升级用户的核心信息。
- **如实性红线**：手册的同步状态必须与事实一致。发帖前确认 `README.md` 导读的基线版本；手册未同步到该版本时写"vX.Y.Z 同步中"，已同步才写"已同步"。
- 单帖完整版的长度控制在 1000-1500 中文字符：足够展开，但不淹没要点。

## 实例参照

完整实例见历史文件：
- `/Users/robotbird/Downloads/pi-durable-v1.1.0-X发布帖.md`（中大型版本：6 项能力 + 破坏性变更 + 精简版）
- `/Users/robotbird/Downloads/pi-durable-v1.2.0-X发布帖.md`（大版本：6 项能力 + 性能数字 + 4 项破坏性变更）
- `/Users/robotbird/Downloads/pi-durable-book-v1.1.0-发布总结.md`（早期三版本格式：主帖/Thread/长文，仅当用户要 Thread 时参考）
