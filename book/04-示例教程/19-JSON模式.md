# 示例 19 · JSON 模式

> **原文**：[`test/examples/19-json.ts`](https://github.com/earendil-works/pi/blob/main/packages/durable/test/examples/19-json.ts)（在原仓库 `packages/durable` 目录下运行）
>
> ```bash
> node --conditions=source --experimental-strip-types test/examples/19-json.ts --events "What is in this directory?"
> ```

## 本例演示

README 把这个例子描述为 "JSON mode: agent events or raw view operations, on SQLite, JSONL, or memory"——等价于 `pi --mode json`：跑一个提示，把整个运行过程以 JSON 行的形式流式输出。它演示了两种输出模式（`--events` 高层 agent 事件流 vs `--ops` 底层视图操作帧）、三种存储后端（`--storage sqlite|jsonl|memory`），以及"先挂监听再提交"的正确顺序。模型与上一例一样双回落：有 key 用 OpenAI，否则 faux。

## 逐段解读

### 参数解析：模式、存储、提示词

```ts
// JSON mode: stream one prompt's run as JSON lines, like `pi --mode json`. Two modes:
//   --events (default): the experimental agent events of watchEvents(), starting with a `snapshot` event.
//   --ops: the raw ConversationView frames, starting with the view itself; each later line holds one commit's ops.
// --storage sqlite (default) | jsonl | memory: sqlite writes a temporary database file, jsonl a temporary directory;
// neither is deleted, and the path is printed to stderr at the end.
// Uses OpenAI when OPENAI_API_KEY is set, and a scripted faux model otherwise.
// Run from packages/durable:
//   node --conditions=source --experimental-strip-types test/examples/19-json.ts --events "What is in this directory?"
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { BACKGROUND_CONTEXT } from "@earendil-works/chord/context";
import { createModels } from "@earendil-works/pi-ai/models";
import { fauxAssistantMessage, fauxProvider, fauxText, fauxToolCall } from "@earendil-works/pi-ai/providers/faux";
import { openaiProvider } from "@earendil-works/pi-ai/providers/openai";
import { NodeExecutionEnv } from "../../src/env/node.ts";
import {
	createRegistry,
	defineExtension,
	Harness,
	MemoryStorage,
	type Storage,
	section,
	watchEvents,
} from "../../src/index.ts";
import { openNodeJsonlStorage } from "../../src/storage/jsonl/node.ts";
import { openNodeSqliteStorage } from "../../src/storage/sqlite/node.ts";
import { createBashTool, createReadTool } from "../../src/tools/index.ts";

const context = BACKGROUND_CONTEXT;
const args = process.argv.slice(2);
const mode = args.includes("--ops") ? "ops" : "events";
const storageIndex = args.indexOf("--storage");
const storageKind = storageIndex < 0 ? "sqlite" : args[storageIndex + 1];
const prompt =
	args.find((arg, index) => !arg.startsWith("--") && (storageIndex < 0 || index !== storageIndex + 1)) ??
	"What is in this directory?";
```

头部注释定义了两种模式：`--events`（默认）输出 `watchEvents()` 的实验性 agent 事件，第一行是 `snapshot` 事件；`--ops` 输出原始的 ConversationView 帧——第一行是视图本身，之后每行是一次 commit 的 ops。存储默认 sqlite（写一个临时数据库文件），jsonl 写临时目录；两者都不删除，路径最后打到 stderr。解析逻辑把 `--storage` 的**取值**排除在提示词候选之外，其余第一个非 `--` 参数作为提示词。

### 三种存储后端

```ts
let storage: Storage;
let location: string | undefined;
if (storageKind === "sqlite") {
	location = join(tmpdir(), `pi-durable-json-${Date.now()}.sqlite`);
	storage = await openNodeSqliteStorage(location);
} else if (storageKind === "jsonl") {
	location = await mkdtemp(join(tmpdir(), "pi-durable-json-"));
	storage = await openNodeJsonlStorage(location, context);
} else if (storageKind === "memory") {
	storage = new MemoryStorage();
} else {
	throw new Error(`Unknown --storage ${storageKind}; use sqlite, jsonl, or memory`);
}
const print = (value: unknown): void => void process.stdout.write(`${JSON.stringify(value)}\n`);
```

三种后端按参数切换：sqlite 落到临时目录里的单个数据库文件（文件名带时间戳），jsonl 落到临时目录，memory 完全不落盘；未知值直接抛错。`print` 工具函数把任意值序列化成一行 JSON 写到 stdout——这就是"JSON 模式"的输出形态。

### 模型与工具装配

```ts
const models = createModels();
let model = { provider: "openai", modelId: "gpt-6-sol" };
if (process.env.OPENAI_API_KEY !== undefined) {
	models.setProvider(openaiProvider());
} else {
	const faux = fauxProvider({ tokensPerSecond: 200 });
	models.setProvider(faux.provider);
	model = { provider: "faux", modelId: "faux-1" };
	faux.setResponses([
		fauxAssistantMessage([fauxToolCall("bash", { command: "ls" }, { id: "call-1" })], { stopReason: "toolUse" }),
		fauxAssistantMessage([fauxText("This directory holds the durable package sources, tests, and docs.")]),
	]);
}

const registry = createRegistry();
registry.install(
	defineExtension({
		name: "coding",
		tools: [createReadTool(), createBashTool()],
		sections: [section("preamble", () => "You are a concise coding assistant.", { tag: false })],
	}),
);
const env = new NodeExecutionEnv({ cwd: process.cwd() });
const harness = await Harness.open(storage, { models, registry, env: () => env }, context);
const root = await harness.root(context, { agent: { model } });
```

装配部分与打印模式示例相同：双模型回落、`coding` 扩展内联声明 read/bash 两个工具、固定 cwd 的执行环境。区别是 faux 建的时候传了 `{ tokensPerSecond: 200 }`——让假模型也以每秒 200 token 的节奏流式输出，这样事件流里能看到真实的增量过程。存储用的是上面选好的后端。

### 先挂监听，再提交

```ts
// Attach before submitting, so the stream covers the whole run.
let stop: () => Promise<unknown>;
if (mode === "events") {
	const stream = await watchEvents(harness, root.id, context);
	print(stream.snapshot);
	stream.start(async (events) => {
		for (const event of events) print(event);
	});
	stop = () => stream.stop();
} else {
	const watch = await root.watch(context);
	print({ view: watch.value });
	watch.start(async (_value, ops) => print({ ops }));
	stop = () => watch.stop();
}
```

注释强调了顺序：**监听要在提交之前挂上，流才能覆盖整个运行**。`--events` 模式：`watchEvents` 建立事件流，第一行先打印 `snapshot`（当前完整状态的快照事件），之后回调按批收到后续事件逐行打印。`--ops` 模式：`root.watch()` 拿到原始视图，第一行打印整个视图，之后每次 commit 只打印它产生的 ops。两种模式都把 `stop` 存起来待会儿停流。

### 运行与收尾

```ts
const submission = await root.submit({ type: "input", content: prompt }, context);
await submission.wait(context);
await harness.waitForIdle(context);
// Let the last batch reach the listener before stopping.
await new Promise((resolve) => setTimeout(resolve, 0));
await stop();
await harness.close(context);
if (location !== undefined) console.error(`${storageKind} storage: ${location}`);
```

这里和打印模式不同：等完自己的 Submission 之后还要 `harness.waitForIdle()`——因为流要覆盖**所有**副作用（工具任务、后续 commit 等），必须等全局空闲。事件回调是在 commit 之后异步执行的，所以停流前用 `setTimeout(0)` 让事件循环转一圈，确保最后一批事件送达监听者。最后关闭 Harness，并把存储位置打到 stderr（临时文件不删除，供检查）。

## 关键点

- JSON 模式提供两种视图：`--events` 是高层 agent 事件流（首行 `snapshot` 快照，之后是增量事件），`--ops` 是底层 ConversationView 帧（首行完整视图，之后每次 commit 一行 ops）——前者适合渲染 UI，后者适合做自定义存储/同步。
- 监听必须在 `submit()` 之前建立，否则会错过运行开头的输出。
- 输出 JSON 的宿主要等 `submission.wait()` **加** `harness.waitForIdle()` 两个条件，再 `setTimeout(0)` 让最后一批事件送达，才能安全停流关闭。
- `--storage` 可在 sqlite（单文件数据库）、jsonl（目录）、memory（不落盘）之间切换；sqlite/jsonl 的临时位置不删除，路径打到 stderr 供事后检查。
- `fauxProvider({ tokensPerSecond: 200 })` 让假模型带流式节奏，事件流里能看到 `message_update` 之类的增量事件，离线也能测流式 UI。
- 工具与系统提示的装配方式与打印模式一致：扩展里内联 `createReadTool()`/`createBashTool()` + `section("preamble", ...)`。
