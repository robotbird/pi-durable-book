# 示例 06 · Harness入门

> **原文**：[`test/examples/06-harness.ts`](../../original/packages/durable/test/examples/06-harness.ts)（在 original/packages/durable 目录下运行）
>
> ```bash
> node --conditions=source --experimental-strip-types test/examples/06-harness.ts
> ```

## 本例演示

Harness 是 Session 之上的高层封装：在 Session 之外加上会话句柄（conversation handles）和持久任务（durable tasks）。本例定义一个带 `read` 工具的 files 扩展并装进 registry，打开 Harness，创建根会话（ID 恒为 1）并注入初始文档，最后展示 agent 配置"存名字、运行时解析"的机制。关键 API：`defineTool`、`defineExtension`、`createRegistry`、`Harness.open`、`harness.root`、`root.agent`、`AgentDoc`。

## 逐段解读

### 1. 导入与概念注释

```ts
// Open a Harness with a registry of extensions.
// Run from packages/durable:
//   node --conditions=source --experimental-strip-types test/examples/06-harness.ts
import { BACKGROUND_CONTEXT } from "@earendil-works/chord/context";
import { Type } from "@earendil-works/pi-ai";
import { createModels } from "@earendil-works/pi-ai/models";
import {
	AgentDoc,
	createRegistry,
	defineDoc,
	defineExtension,
	defineTool,
	Harness,
	MemoryStorage,
} from "../../src/index.ts";

const context = BACKGROUND_CONTEXT;
```

除了 chord 和 durable 本体，这里还从 pi-ai 导入了 `Type`（声明工具参数 schema 用）和 `createModels`（模型访问层）。`AgentDoc` 是 Harness 内建的 agent 配置文档，稍后用来读取存储的选择。

### 2. 工具、扩展与 registry

```ts
// A Harness is a Session plus conversation handles and durable tasks. Extension
// code (tools, prompt sections, hooks, tasks) comes in named extensions
// installed in a registry the application owns. Nothing in the registry is
// saved; it is this process's code.
const read = defineTool({
	name: "read",
	description: "Read a file",
	parameters: Type.Object({ path: Type.String() }),
	execute: async (args) => ({ content: [{ type: "text", text: `contents of ${args.path}` }] }),
});
const Files = defineExtension({ name: "files", tools: [read] });
const registry = createRegistry();
registry.install(Files);
```

头注释给出 Harness 的定义：Session + 会话句柄 + 持久任务；扩展代码（工具、prompt section、hook、任务）以命名扩展的形式装进应用持有的 registry，registry 里的东西不落盘——它就是本进程的代码。`defineTool` 用 pi-ai 的 `Type.Object` 声明参数 schema，`execute` 返回文本内容；`defineExtension` 把工具打包成名为 "files" 的扩展；`createRegistry()` 建注册表，`registry.install()` 完成安装。

### 3. 打开 Harness

```ts
// `models` is pi-ai's model access; generation calls models through it.
const harness = await Harness.open(new MemoryStorage(), { models: createModels(), registry }, context);
```

`Harness.open()` 除了存储后端，还需要 `models`（pi-ai 的模型访问层，所有生成调用都经由它）和刚才的 `registry`。

### 4. 定义文档并创建根会话

```ts
const Notes = defineDoc<{ text: string }>({
	kind: "example.notes",
	version: 1,
	scope: "conversation",
	history: "rewindable",
	fork: "asOf",
	initial: () => ({ text: "" }),
});

// The root conversation always has ID 1. The first root() call creates it,
// its built-in documents, the `agent` choices, and whatever `init` writes, all
// in one commit. Later calls, including after a restart, return it and ignore
// both options.
const root = await harness.root(context, {
	agent: { thinkingLevel: "low" },
	init: async (tx, rootId) => {
		(await tx.doc(Notes, rootId)).text = "root notes";
	},
});
```

根会话的 ID 恒为 1。第一次调用 `harness.root()` 会一次性创建：根会话本身、它的内建文档、`agent` 选项（这里是 `thinkingLevel: "low"`），以及 `init` 回调写入的内容——全部在一个 commit 里。之后的调用（包括进程重启之后）原样返回它，并忽略两个选项。`init` 里用熟悉的 `tx.doc()` 给 Notes 写入 "root notes"。

### 5. 存的是名字，用的是对象

```ts
console.log("root:", root.id, await harness.snapshot(Notes, root.id, context));
// The stored choices are names; agent() resolves them against the registry.
console.log("stored agent:", await harness.snapshot(AgentDoc, root.id, context));
const agent = await root.agent(context);
console.log(
	"resolved:",
	agent.thinkingLevel,
	agent.extensions.map((extension) => extension.name),
	agent.tools.map((tool) => tool.name),
);

await harness.close(context);
```

`harness.snapshot(AgentDoc, ...)` 读出根会话存储的 agent 选择——注意里面存的是扩展和工具的名字，不是对象。`root.agent()` 把这些名字对着 registry 解析成真正的对象，打印出解析后的 thinkingLevel、扩展名列表和工具名列表。最后关闭 Harness。

## 关键点

- Harness = Session + 会话句柄 + 持久任务；扩展（工具/section/hook/任务）按名字组织进 registry。
- registry 不持久化：存储里只存名字，实现由本进程的代码提供。
- `harness.root()` 是幂等的：首次调用一次性创建 ID 恒为 1 的根会话、内建文档、agent 选择和 init 产物（一个 commit）；重启后再调用原样返回并忽略选项。
- agent 配置按名字存储（内建的 `AgentDoc`），`root.agent()` 在运行时对着 registry 解析成真正的对象。
- `models` 是 pi-ai 的模型访问层，Harness 的生成调用都走它。
- 这套"存名字、查 registry"的设计，正是示例 07 中卸载/重装扩展语义的基础。
