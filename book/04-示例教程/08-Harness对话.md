# 示例 08 · Harness 对话

> **原文**：[`test/examples/08-harness-conversations.ts`](https://github.com/earendil-works/pi/blob/main/packages/durable/test/examples/08-harness-conversations.ts)（在原仓库 `packages/durable` 目录下运行）
>
> ```bash
> node --conditions=source --experimental-strip-types test/examples/08-harness-conversations.ts
> ```

## 本例演示

打开一个 Harness 后，演示对话（conversation）层面最常用的几个操作：用 `defineEntry` 定义带类型的条目并通过 `commit` 写入、用 `harness.createConversation()` 新建对话、用 `fork()` 从某个条目处分叉出新对话，以及用 `harness.conversation()` 按 id 查找。它还顺带说明了对话句柄（handle）本身是无状态的、如何配置 agent 的思考级别。

## 逐段解读

### 准备 Harness 与根对话

```ts
import { BACKGROUND_CONTEXT } from "@earendil-works/chord/context";
import { createModels } from "@earendil-works/pi-ai/models";
import { createRegistry, defineEntry, Harness, MemoryStorage } from "../../src/index.ts";

const context = BACKGROUND_CONTEXT;
const harness = await Harness.open(
	new MemoryStorage(),
	{ models: createModels(), registry: createRegistry() },
	context,
);
const root = await harness.root(context);
await root.configure({ thinkingLevel: "high" }, context);
```

`Harness.open` 打开一个基于内存存储（`MemoryStorage`）的 harness，并注入模型表和空的扩展注册表。pi-durable 的每个 API 末尾都带一个 `context` 参数，示例统一使用 `BACKGROUND_CONTEXT`。`harness.root()` 返回根对话的句柄，`configure()` 直接修改该对话的 agent 配置——这里把思考级别设为 `high`。

### 定义类型化条目并提交

```ts
// Conversation handles are stateless; compare them by id. They bind commits
// to their conversation. An entry token types an entry kind's `data`.
const Message = defineEntry<{ from: string }>("message");
const hello = await root.commit(
	(tx) =>
		tx.appendEntry(Message, root.id, {
			data: { from: "example" },
			model: [{ role: "user", content: "hello", timestamp: 1 }],
		}),
	context,
);
console.log("typed entry:", Message.is(hello), hello.data.from);
```

这段先解释了对话句柄的语义：句柄是无状态的对象，比较对话要按 `id`；句柄的作用是把 `commit` 绑定到它所代表的对话上。`defineEntry<{ from: string }>("message")` 创建一个"条目令牌"，它为 `message` 这种条目类型的 `data` 字段提供 TypeScript 类型。提交时 `tx.appendEntry(Message, root.id, ...)` 把条目写进 `root.id` 指向的对话：`data` 是给应用自己用的数据，`model` 是该条目对下一次模型请求贡献的消息。提交返回的条目可以用令牌上的 `Message.is(hello)` 做类型收窄，之后就能直接访问 `hello.data.from`。

### 新建对话与分叉

```ts
// createConversation() and fork() apply `agent` and run `init` in the
// creating commit. A fork starts with the agent the parent had at the fork
// entry.
const helper = await harness.createConversation(
	{ ownership: { kind: "ownerless" }, agent: { thinkingLevel: "minimal" } },
	context,
);
const retry = await root.fork(hello.id, { ownership: { kind: "ownerless" } }, context);
console.log("helper thinking:", (await helper.agent(context)).thinkingLevel);
console.log("fork thinking:", (await retry.agent(context)).thinkingLevel);
console.log("lookup:", (await harness.conversation(retry.id, context))?.id === retry.id);
```

`createConversation()` 和 `fork()` 有共同语义：两者都会在"创建提交"里应用传入的 `agent` 配置并运行 `init`。区别在于来源——新建的 `helper` 对话使用选项里显式给出的 `thinkingLevel: "minimal"`；而 `retry` 是从根对话的 `hello` 条目处分叉出来的，它继承的是**父对话在该分叉点时的 agent 状态**（而不是父对话当前的配置）。两种对话都声明了 `ownership: { kind: "ownerless" }`（无主对话，不归属于某个父对话）。最后 `harness.conversation(retry.id, context)` 演示按 id 查找对话，返回的句柄 id 与原 id 一致。

### 收尾

```ts
await harness.close(context);
```

用完后关闭 harness，释放存储等资源。

## 关键点

- 对话句柄是无状态视图：判断两个句柄是否指向同一对话要比较 `id`，而不是比较对象；句柄保证 `commit` 写到正确的对话里。
- `defineEntry` 的条目令牌一举两得：给 `data` 提供类型，又提供 `.is()` 做运行时类型收窄。
- `createConversation()` 与 `fork()` 都会在创建提交里应用 `agent` 配置并运行 `init`，因此新对话的初始配置是随第一条记录一起持久化的。
- `fork()` 的新对话从"分叉点条目"处父对话所拥有的 agent 状态起步，不一定等于父对话现在的配置。
- `ownership` 决定对话归属：`ownerless` 是独立对话，归属某对话则生命周期随之管理。
- 需要"找回"对话时用 `harness.conversation(id)`，查不到会返回 `undefined`（示例用 `?.` 处理）。
