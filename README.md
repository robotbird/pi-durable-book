# 《pi-durable：持久化智能体运行时》中文手册

> 本书记录了 [`@earendil-works/pi-durable`](https://github.com/earendil-works/pi/tree/main/packages/durable) 的全部文档与示例内容，由英文原版翻译、整理而成。全书内容基于 **v1.0.2**（2026-10-04，当前 npm `latest`）。
>
> **原文声明**：该项目为实验性（Experimental）项目，API 可能在版本间不经通知即发生变更。

## 这是什么

`pi-durable` 是一个**持久化智能体运行框架（durable agent harness）**：对话、模型轮次、工具调用以及你自己的应用状态，在任何内容被展示之前都会先提交到存储。如果进程在某一轮执行中途崩溃，重新打开存储即可从上次中断的地方继续工作。

它构建在两个基础库之上：

- [`@earendil-works/pi-ai`](https://github.com/earendil-works/pi/tree/main/packages/ai) —— 模型访问层；
- [`@earendil-works/chord`](https://github.com/earendil-works/pi/tree/main/packages/chord) —— 文档状态层。

## 全书结构

本书分四篇，与原始仓库的内容一一对应：

| 篇章 | 内容 | 对应原文 |
|---|---|---|
| **第一篇 概述与快速上手** | README 全文中文版：安装、快速上手、27 个主题的使用指南 | `README.md` |
| **第二篇 规范说明书** | Pico5 规范全文中文版（13 章），按主题拆为 6 节 | `docs/spec.md` |
| **第三篇 设计文档** | 实现计划、Chord 使用方式、Chord 差异调研 | `docs/pico-v5-handoff.md` 等 3 篇 |
| **第四篇 示例教程** | 32 个可运行示例的中文逐段解读，从会话基础到完整编码智能体 | `test/examples/` |

原始仓库文件（含源码与测试，未翻译）完整保存在 [`original/`](original/packages/durable/README.md) 目录中，供对照查阅。

## 如何阅读

- **想快速了解能做什么**：读第一篇的"快速上手"，再浏览第四篇的示例 14-19（聊天、流式、打印模式、JSON 模式）。
- **想理解设计原理**：读第二篇规范说明书，配合第三篇实现计划。
- **想动手实践**：按第四篇示例教程逐个运行，示例 00-13 讲底层机制（会话、文档、分叉、监听、Harness），示例 14-31 讲完整用法（子代理、压缩、编码智能体、计划模式等）。

## 运行示例

在 `original/packages/durable`（或原仓库的 `packages/durable`）目录下执行：

```bash
node --conditions=source --experimental-strip-types test/examples/14-chat.ts
```

调用 OpenAI 的示例需要设置 `OPENAI_API_KEY` 环境变量；其余示例默认使用 faux（假）模型提供方。

## 目录

完整目录见 [SUMMARY.md](SUMMARY.md)。

## 许可

原项目采用 MIT 许可证。
