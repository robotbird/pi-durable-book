# Pico5 通过 Chord 使用文档

> **本篇译自** [`docs/pico-v5-chord-usage.md`](https://github.com/earendil-works/pi/blob/main/packages/durable/docs/pico-v5-chord-usage.md)——本包对 Chord 的使用方式。

本指南使用 [Pico5 规范](https://github.com/earendil-works/pi/blob/main/packages/durable/docs/spec.md) 中的契约。其代码以 `test/chord-guide.test.ts` 编译并运行；请保持两者同步。

- **Session：** 承载会话（conversation）、条目、任务与文档的持久容器；它把所有变更串行化到一条提交执行线上。
- **Facet：** Chord 宿主中一个功能的装配单元。setup 同步地声明服务与依赖；`onActivate` 在依赖就绪之后运行。
- **Context：** 显式传递的取消与调用值。请转发调用方的 context。
- **Service：** 带类型的 token 及其实现，通过 `env.use` 获取。远程服务包含复制状态与带 JSON 参数、末尾附加 `Context` 的异步方法。
- **持久文档（durable document）：** 以完整 base、Chord 操作与检查点（checkpoint）形式持久化的 JSON。其定义 token 声明 schema、版本、作用域与初始化；会话作用域还声明历史与 fork 行为。
- **事务 draft（transaction draft）：** `await tx.doc` 返回的可吊销写时复制（copy-on-write）对象，仅在该提交回调内部有效，包括所有嵌套对象。
- **DocumentState：** 绑定到单个文档化身的可释放只读 Chord 状态。
- **ReplicatedState：** Chord 的不可变完整值，通过 `value` 与 `subscribe(listener)` 访问。`value` 在水合（hydrate）之前或断连时为 `undefined`。监听器收到 `(value, context, delivery)`；delivery 包含 `kind`（`hydrate` 或 `update`）与流 `sequence`，而不是 Session 提交编号。

文档直接作用于某个 Session、会话或任务。任务是附加到会话上的持久工作；当任务进入终态时，它的文档随之退役，并且绝不参与会话 fork。

## 导入与适配器边界

各示例层层递进。`ConversationRecord`、`EntryRecord` 与 `TaskRecord` 是持久化记录，而 `Conversation` 是公开的会话对象，`Entry`/`Task` 是带类型的定义。导入如下：

```ts
import {
  createFacetHost, createRemoteServiceBinding, defineFacet, defineService,
  type Context, type Facet, type FacetHost, type RemoteServiceTransport, type ReplicatedState,
} from "@earendil-works/chord";
import { BACKGROUND_CONTEXT } from "@earendil-works/chord/context";
import {
  type ConversationId, defineDoc, defineDocFamily, type DocumentObserver,
  type Harness, type Session, type TaskId, type TaskRuntime,
} from "@earendil-works/pi-durable";
```

`Harness` 就是一个 `Session`，因此下文每个函数也都可以传入一个已打开的 Harness。

`documentState()` 在内部完成 Chord 采纳（adoption）：它原子地捕获一个已提交快照，注册接收此后每个精确帧，并返回一个已完成水合的只读状态。快照已覆盖的操作绝不重投。释放该状态只是解除观察，并不是删除文档。Pico 仍是唯一的修改者。

## 1. Session 级画布

本 Session 中的所有会话共享同一个画布。Session 文档是 current-only 的，没有历史或 fork 设置。

```ts
type Stroke = { color: string; points: { x: number; y: number }[] };
type CanvasState = { strokes: Stroke[] };

const CanvasDoc = defineDoc<CanvasState>({
  kind: "app.canvas", version: 1, scope: "session",
  initial: () => ({ strokes: [] }),
  // Store a complete base after at most 99 replayed deltas.
  checkpointWhen: (_value, _ops, info) => info.deltasSinceBase >= 99,
});

interface CanvasService {
  readonly state: ReplicatedState<CanvasState | null>;
  addStroke(stroke: Stroke, context: Context): Promise<void>;
}
const Canvas = defineService<CanvasService>("app.canvas");

async function createCanvasFacet(session: Session, context: Context): Promise<Facet> {
  // Creation is explicit; observation never writes.
  await session.commit(async tx => {
    await tx.doc(CanvasDoc);
  }, context);
  const state = await session.documentState(CanvasDoc, context);
  if (state === undefined) throw new Error("canvas was retired during setup");
  return defineFacet({
    id: "app.canvas/session",
    setup(env) {
      env.own(() => state.dispose());
      env.provide(Canvas, {
        state,
        async addStroke(stroke, context) {
          await session.commit(async tx => {
            const draft = await tx.doc(CanvasDoc);
            draft.strokes.push(stroke); // Chord copies the assigned stroke by value.
          }, context);
        },
      });
    },
  });
}

const CanvasConsumer = defineFacet({
  id: "app.canvas/consumer",
  setup(env) {
    const canvas = env.use(Canvas); // Declare now; access only after activation.
    env.onActivate(() => {
      env.own(canvas.state.subscribe((value, _context, delivery) => {
        console.log(delivery.kind, delivery.sequence, value?.strokes.length ?? "retired");
      })); // subscribe delivers the current hydrated value, then updates.
    });
  },
});

async function runCanvasExample(session: Session): Promise<void> {
  const context = BACKGROUND_CONTEXT;
  const provider = await createCanvasFacet(session, context);
  const host = await createFacetHost({ facets: [provider, CanvasConsumer] });
  try {
    await host.services.use(Canvas).addStroke({
      color: "black", points: [{ x: 10, y: 20 }, { x: 30, y: 40 }],
    }, context);
  } finally {
    await host.dispose(); // Unsubscribes; does not delete the canvas or close Session.
  }
}
```

应用程序拥有打开的 Session。在同步 `setup` 之前异步获取文档状态，然后把它的释放权移交给 facet；`env.provide` 不能在 `onActivate` 里运行。每个 Session 宿主安装一个提供者（provider）。Chord 可以独立地重载展示类 facet。Session 侧的工具、hook、任务与提示词 section 则通过 Harness 注册表重载：以同名安装替代扩展（规范 7.5 节）。已在运行的工作保留旧代码，因此 facet 需要自己管理旧资源的生命周期。

远程客户端提供一个连接到宿主 `services` 提供者的 `RemoteServiceTransport`；Chord 不规定套接字协议。`CanvasConsumer` 在配置了远程服务源的 UI 宿主中也原样可用。

```ts
async function connectCanvas(transport: RemoteServiceTransport, context: Context) {
  const services = createRemoteServiceBinding({ services: [Canvas], transport });
  const canvas = services.use(Canvas);
  const stop = canvas.state.subscribe((value, _context, delivery) => {
    console.log(delivery.kind, delivery.sequence, value?.strokes ?? "retired");
  });
  try {
    await services.ready(context); // Initial snapshot installed; not all future updates.
  } catch (error) {
    stop();
    await services.dispose(BACKGROUND_CONTEXT);
    throw error;
  }
  return async () => {
    stop();
    await services.dispose(BACKGROUND_CONTEXT);
  };
}
```

```text
explicit first tx.doc -> commit base { strokes: [] }
addStroke(A)       -> commit A -> local and remote subscribers see A
worker restarts   -> open same durable storage; install canvas facet again
acquire source    -> load base + committed deltas, without rerunning initial()
late client       -> hydrate complete canvas including A, then ordered updates
conversation fork -> still uses this same Session canvas
```

要让重启之后状态仍然存活，请使用持久存储。内存后端不是持久的。一个方法的提交成功并不承诺每个远程回调都已运行。

按相反顺序关闭：先分离客户端并释放 facet 宿主——这会撤回其服务并释放它拥有的文档状态——然后关闭 Harness。如果先关闭 Harness，状态会在客户端仍然连接时终结：它们保留最后一个值，且永不再更新。

```ts
async function shutdown(host: FacetHost, detachClients: () => Promise<void>, harness: Harness, context: Context) {
  await detachClients();
  await host.dispose();
  await harness.close(context);
}
```

## 2. 会话作用域的 diff 评审

**文档家族（document family）**用一个定义对应多个实例。逻辑键是 `(kind, conversationId, key)`；持久化的数字文档 ID 标识一个化身，绝不复用。创建 seed 不是键的一部分。

```ts
type ReviewInput = { path: string; patch: string };
type ReviewComment = { id: string; line: number; text: string };
type ReviewState = ReviewInput & { comments: ReviewComment[] };
const ReviewDoc = defineDocFamily<ReviewState, ReviewInput>({
  kind: "app.diff-review", version: 1, family: true, scope: "conversation",
  history: "latest", fork: "current",
  initial: seed => ({ path: seed.path, patch: seed.patch, comments: [] }),
  checkpointWhen: (_value, _ops, info) => info.deltasSinceBase >= 49,
});
interface DiffReviewService {
  readonly state: ReplicatedState<ReviewState | null>;
  identity(context: Context): Promise<{ conversationId: ConversationId; key: string }>;
  addComment(comment: ReviewComment, context: Context): Promise<void>;
}
const DiffReviews = defineService<DiffReviewService>("app.diff-reviews");

function reviewFacet(
  session: Session, conversationId: ConversationId,
  reviews: readonly { key: string; seed: ReviewInput }[], context: Context,
): Facet {
  return defineFacet({
    id: "app.diff-reviews/session",
    setup(env) {
      const instances = env.provideMany(DiffReviews);
      env.onActivate(async () => {
        for (const review of reviews) {
          await session.commit(async tx => {
            await tx.doc(ReviewDoc, conversationId, review.key, review.seed);
          }, context);
          const state = await session.documentState(ReviewDoc, conversationId, review.key, context);
          if (state === undefined) throw new Error("review was retired during setup");
          env.own(() => state.dispose());
          // Chord instance keys route services; they are not numeric document incarnation IDs.
          instances.spawn(JSON.stringify([conversationId, review.key]), {
            state,
            async identity() { return { conversationId, key: review.key }; },
            async addComment(comment, context) {
              await session.commit(async tx => {
                const draft = await tx.doc(ReviewDoc, conversationId, review.key, review.seed);
                draft.comments.push(comment); // Chord copies the assigned comment by value.
              }, context);
            },
          }); // The facet owns spawned service lifetimes automatically.
        }
      });
    },
  });
}
```

示例输入：`[{ key: "review-7", seed: { path: "a.ts", patch: "-old\n+new" } }]`。请传入互不相同的家族 key 与真实的会话 ID，并按上文安装 facet。带键的消费者使用 `env.observe(DiffReviews, handler)`，而不是 `env.use`。处理器收到 `(review, context)`；用 `review.identity(context)` 识别它，用 `review.state.subscribe` 观察评论。

这些评论是会话作用域的：结束生成任务或卸载 facet 都不会使它们退役。`current` 在 fork 提交时把每个逻辑上存在的评审复制为带新数字 ID 的独立子实例，并保留家族 key。此后父子各自分叉。

```text
parent review-7: comment A -> transcript entry E -> comment B
fork at E with current: child review-7 contains A and B
child adds C: parent still contains only A and B
```

使用 `fork: "initial"` 时，任何实例都不复制；第一个子实例的 `tx.doc()` 使用其提供的 seed。`latest` 不能读取历史，也不能在 fork 时使用 `asOf`；要反映 E 的提交，请使用 `history: "rewindable"` 加 `asOf`。重新访问会忽略后续的 seed；要更新 patch，需要显式变更或使用不同的评审 key。

## 3. 任务作用域的输出与工具/任务 watch

这是一个有界的进度窗口，不是永久结果。作用域本身就赋予了它任务生命周期；不需要历史、fork、owner 或会话设置。

```ts
type JobInput = { command: string };
type JobOutput = { stdout: string; chunks: number };
const JobOutputDoc = defineDoc<JobOutput>({
  kind: "app.job-output", version: 1, scope: "task",
  initial: () => ({ stdout: "", chunks: 0 }),
  checkpointWhen: (_value, _ops, info) => info.deltasSinceBase >= 99,
});
async function appendJobOutput(
  runtime: TaskRuntime<JobInput, { phase: "running" }, null, object>,
  chunk: string, context: Context,
): Promise<void> {
  // Read process output outside this callback. The runtime gates the live task.
  await runtime.commit(async tx => {
    const draft = await tx.doc(JobOutputDoc, runtime.taskId);
    draft.stdout = (draft.stdout + chunk).slice(-50_000);
    draft.chunks += 1;
  }, context);
}
async function observeJob(
  api: DocumentObserver, producerTaskId: TaskId,
  finished: Promise<void>, context: Context,
): Promise<void> {
  const watch = await api.watchDoc(JobOutputDoc, producerTaskId, context);
  if (watch === undefined) return;
  console.log(watch.value === null ? "retired" : watch.value.stdout);
  try {
    watch.start(async (value, ops, _context) => {
      await sendCommittedFrame(value, ops);
      await render(value === null ? "retired" : value.stdout);
    }); // Serialized callbacks never overlap.
    await finished; // Caller-supplied observation lifetime; outside any commit.
  } finally {
    await watch.stop(); // Idempotent; prevents another callback from starting.
  }
}
```

运行阶段会调用 `appendJobOutput`，同时必须提交它的下一个检查点或终态结果。`api` 是该调用的 `DocumentObserver`；`TaskRuntime` 包含这个接口。`tx.doc()` 创建会校验目标任务仍然存活，并从任务记录推导其会话。任务终态且其文档退役之后，随后的非创建 watch 查找返回 `undefined`。

```text
watchDoc: capture immutable V0 + register for later exact committed frames
producer commits D1 and D2 before start: buffer (V1, D1), (V2, D2)
start: caller has initialized from V0; deliver D1, then D2 serially
producer commits D3 while listener awaits: buffer D3; never overlap callbacks
101 pending frames: replace the pending suffix with [["r", newestValue]]
producer becomes terminal: deliver [["r", null]], then close as retired
```

watch 在其所属调用结束时自动停止。通过 Session 获取的 watch 归调用方所有，并在 Session 关闭时停止。已投递的快照绝不变异。慢的或未开始的投递最多保留 100 个精确帧，然后用一个全值根替换替换掉未投递后缀。watch 是收敛的状态观察，而不是转换日志。退役会结束该化身的流；暴露该状态的服务必须随之撤回，或保持在 `null`。重建需要新的 watch/状态与新的数字文档 ID。终态任务无法再产生输出。任务作用域文档绝不复制进 fork。请在退役之前的终态提交中，把需要的输出保存在结果条目或 Session/会话作用域文档里。只有当一个任务需要多个独立 keyed 的文档时，才使用任务作用域家族。

## 4. 内置会话视图与提交投递

`ConversationView` 包含 `conversation`、原始记录 `entries`，以及 `docs: Readonly<Record<string, JsonObject>>`。选定的内置单例按稳定的文档 kind 挂载到 `docs` 之下，而不是按数字化身 ID。规范中的示例路径映射是：

```text
document ["s", ["generation", "message"], value]
 -> view ["s", ["docs", "pi.live", "generation", "message"], value]
```

`pi.live` 规定于 `spec.md` 8.2 节。挂载在每个完整 Session 提交上发布一个批次：条目/head 变更与变更过的已挂载文档一起发布，无需 tracker 或语义投影。第三方文档**不会自动挂载**；请使用它们自己的 Chord 服务或受信任的调用 watch。已退役的源会发布 `null`；此时动态服务应当撤回其实例，而不是暴露过期数据。

```text
addStroke -> hold Session mutation line -> await tx.doc -> mutate tracker change draft
callback succeeds -> tracker prepare: immutable candidate + immutable ops
Session checkpoint predicate selects a base or delta exactly once
atomic storage commit: persist selected document and record writes
storage succeeds -> adopt candidate + enqueue candidate/ops, still on line
release line -> deliver committed source ops -> adapter -> local/remote Chord consumers
late subscriber -> atomically capture committed value + adapter sequence + subscription
```

不存在"可见但不持久"的路径。回调、tracker 准备与检查点失败在存储层准入之前正常中止。不确定的存储层失败不发布任何内容，并使打开的 Session 中毒；此时应当关闭并重开它，而不是继续运行。

## 陷阱（footguns）

- 绝不在提交之间保留 draft、嵌套代理或绑定的数组方法；它们会被吊销。被赋值的容器按值复制。
- 异步提交在存储结算与基线采纳期间一直持有执行线。在那里应当等待的是文档访问，而不是模型、进程、网络调用或人。
- 只有 `tx.doc()` 会创建。`snapshot`、`documentState` 与 `watchDoc` 在缺席时返回 `undefined`，绝不写入。家族 seed 只在首个 `tx.doc()` 创建化身时使用；后续 seed 被忽略。
- 在 `start()` 之前从固定的 `watch.value` 完成初始化。慢的或未开始的投递最多保留 100 个精确帧，然后用一个全值根替换替换掉待处理后缀。不做任何序列化字节记账。不要把 watch 当作审计日志使用。
- `stop()` 会阻止未来的回调，但不会中止、也不会等待一个已在运行的回调。
- 检查点由定义说了算，而不是存储启发式。保持文档 kind、版本、fork 策略与公开路径稳定；schema 变更需要迁移，而不是只改源码重命名。

Chord 源码（见原仓库 `packages/chord`）：[types](https://github.com/earendil-works/pi/blob/main/packages/chord/src/types.ts)、[facet 示例](https://github.com/earendil-works/pi/blob/main/packages/chord/test/facets.test.ts)、
[state](https://github.com/earendil-works/pi/blob/main/packages/chord/src/services/state.ts)、[provider](https://github.com/earendil-works/pi/blob/main/packages/chord/src/services/provider.ts)、
[Context](https://github.com/earendil-works/pi/blob/main/packages/chord/src/context/index.ts)、[Delta](https://github.com/earendil-works/pi/blob/main/packages/chord/src/delta/README.md)。
