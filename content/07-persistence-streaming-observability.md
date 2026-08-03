# 第 7 章：持久化、流式与观测

## 学习目标

理解 LangGraph 如何通过 checkpointer 和 `thread_id` 保存线程状态，以及如何在运行时用 `astream_events` 和 `get_state()` 观察图执行。

## 它是什么

checkpointer 负责把图状态按线程保存下来；`thread_id` 决定“哪几次调用属于同一条会话”。`astream_events` 提供运行时事件流，适合看节点、模型和状态更新过程；`get_state()` 则用于在某个时刻直接读取该线程的状态快照。LangSmith 不是另一套执行机制，而是把这些运行轨迹发到外部观测平台里。

## 当前项目怎么用

当前仓库的 `deep_researcher` 本身没有在源码里直接编译 checkpointer：

```python
deep_researcher = deep_researcher_builder.compile()
```

这意味着项目核心图默认是“无持久化”的，适合本地直接跑。但 LangGraph 官方文档说明：

- 若要持久化线程记忆，需要在 `compile(checkpointer=...)` 时提供 saver。
- 同一 `thread_id` 的多次调用会共享状态。
- `get_state(config, subgraphs=True)` 可查看子图状态。
- `astream_events(..., version="v3")` 可以流式看到运行中的事件。

当前依赖里 `InMemorySaver` 可直接用于学习和测试；它只保存在内存里，进程重启后数据就没了。

## LangSmith 放在哪

LangSmith 是外部观测平台，不改变图本身的状态机制。只要你的模型调用链已带 LangChain/LangGraph instrumentation，并且配置了 `LANGSMITH_TRACING=true` 和有效 API key，同一运行就会自动出现在 LangSmith 里。这个章节默认不主动发 traces 到外部服务，只验证本地 `astream_events` 和 `get_state()`。

## 最小真实 Agent

示例文件：[07_persistence_streaming_observability.py](/knowledge-notes/examples/langgraph-langchain/examples/07_persistence_streaming_observability.py)。

它做三件事：

1. 用 `InMemorySaver()` 编译一个只有一个模型节点的图。
2. 用同一个 `thread_id` 连续调用两次：
   - 第一次告诉模型“我叫老李”。
   - 第二次问“我刚才说我叫什么？”。
3. 在第一次调用时用 `astream_events(..., version="v3")` 统计事件数量；第二次后用 `get_state(config)` 查看线程里累计消息数。

## 运行

```bash
uv run python docs/langgraph-learning/examples/07_persistence_streaming_observability.py
```

预期现象：

1. 打印第一轮 `事件数`。
2. 第二轮回答能回忆出名字。
3. `持久化消息数` 大于 2，说明第一轮内容已保存在同一线程里。

## 常见误区

**以为 `thread_id` 只是日志标签。** 不是。没有相同 `thread_id`，同一个 checkpointer 也不会把两次调用接成同一线程。

**以为 `InMemorySaver` 就算长期记忆。** 不是。它只适合本地学习、测试和单进程调试，进程一重启全没了。

**以为开了 LangSmith 才能看运行过程。** 不对。`astream_events` 和 `get_state()` 本地就能用；LangSmith 是把这些轨迹发到外部平台方便检索、比较和评估。

## 本次真实验证

已使用默认 `openai:gpt-5.5` 运行一次。结果为：

```text
事件数: 20
第二轮答复: 你刚才说你叫老李。
持久化消息数: 4
```

运行时出现 `v3 streaming protocol on Pregel is experimental` 告警，这是当前版本对 `astream_events(..., version="v3")` 的 beta 提示，不影响本次结果。
