# 示例 04 · Chord状态

> **原文**：[`test/examples/04-chord-state.ts`](../../original/packages/durable/test/examples/04-chord-state.ts)（在 original/packages/durable 目录下运行）
>
> ```bash
> node --conditions=source --experimental-strip-types test/examples/04-chord-state.ts
> ```

## 本例演示

如何把一个文档暴露成 Chord 的响应式状态。`session.documentState()` 返回一个绑定到文档的只读 Chord 状态，`subscribe()` 可以订阅它的每一次变更推送；事务里的一次普通赋值就会触发订阅回调，回调能拿到值、投递类型（`delivery.kind`）和序号（`delivery.sequence`）。

## 逐段解读

### 1. 准备：会话与初始文档

```ts
// Expose a document through Chord.
// Run from packages/durable:
//   node --conditions=source --experimental-strip-types test/examples/04-chord-state.ts
import { BACKGROUND_CONTEXT } from "@earendil-works/chord/context";
import { createSession, defineDoc, MemoryStorage } from "../../src/index.ts";

const context = BACKGROUND_CONTEXT;
const session = createSession(new MemoryStorage());

const Notes = defineDoc<{ text: string }>({
	kind: "example.notes",
	version: 1,
	scope: "conversation",
	history: "rewindable",
	fork: "asOf",
	initial: () => ({ text: "" }),
});
const chat = await session.commit(async (tx) => {
	const conversation = await tx.createConversation({ ownership: { kind: "ownerless" } });
	(await tx.doc(Notes, conversation.id)).text = "first";
	return conversation;
}, context);
```

准备工作：定义熟悉的 Notes 文档，并在创建会话的同一个 commit 里写入初始值 "first"——这保证了"会话存在"与"文档有初值"原子地同时发生，后面订阅才一定有东西可读。

### 2. 拿到只读 Chord 状态并订阅

```ts
// documentState() never creates a document. It returns a hydrated read-only
// Chord state bound to the current concrete incarnation.
const notesState = await session.documentState(Notes, chat.id, context);
if (notesState === undefined) throw new Error("notes are absent");
const stopNotes = notesState.subscribe((value, _deliveryContext, delivery) => {
	console.log("Chord notes:", delivery.kind, delivery.sequence, value);
});
```

`session.documentState()` 从不创建文档：文档不存在时返回 undefined（所以示例先判空再继续）。它返回的是一个"已注水"（hydrated，即已加载好当前值）的只读 Chord 状态，绑定到文档当前的具体化身（incarnation）。`subscribe()` 注册订阅回调并返回取消订阅函数 `stopNotes`；回调参数是 `(value, deliveryContext, delivery)`，其中 `delivery.kind` 是投递类型、`delivery.sequence` 是投递序号。

### 3. 提交变更并观察推送

```ts
await session.commit(async (tx) => {
	(await tx.doc(Notes, chat.id)).text = "published through Chord";
}, context);
stopNotes();
notesState.dispose();

await session.close(context);
```

在事务里把文档改成 "published through Chord"，这次提交会驱动订阅回调打印出新的值和投递信息。随后 `stopNotes()` 取消订阅、`notesState.dispose()` 释放状态资源，最后关闭 Session。

## 关键点

- `documentState()` 是纯读端：绝不创建文档，不存在就返回 undefined；想创建得在事务里用 `tx.doc()`。
- 返回的 Chord 状态是只读的；修改文档仍然只能走 `session.commit()` 事务，变更会自动推给订阅者。
- 订阅回调携带投递元信息：`delivery.kind`（投递类型）和 `delivery.sequence`（序号），可用于区分推送类型与排序。
- `subscribe()` 返回取消订阅函数；状态对象用完要 `dispose()` 释放。
- 这种订阅是"推送观察"；需要异步、串行地处理变更时，改用示例 05 的 watch。
