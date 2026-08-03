# 第 6 章：子图与并发

## 学习目标

理解当前项目为什么拆出 supervisor 子图和 researcher 子图，以及父图如何并发调用多个 researcher 子图后再汇总结果。

## 它是什么

子图是已经编译好的 LangGraph，可以作为父图的一个节点，也可以在父节点内部被调用。当前项目中父子图状态 schema 不同，所以 supervisor 在节点内部把工具调用转换成 researcher 输入，再调用 `researcher_subgraph.ainvoke(...)`。`asyncio.gather` 用来同时启动多个 researcher，提高吞吐，但也会放大模型请求和工具调用成本。

## 当前项目怎么用

当前主实现有三层：

| 层级 | 图 | 职责 |
| --- | --- | --- |
| 外层图 | `deep_researcher` | 澄清用户、生成 research brief、调用 supervisor 子图、生成最终报告 |
| supervisor 子图 | `supervisor_subgraph` | 决定要不要继续研究、是否发起多个 `ConductResearch` |
| researcher 子图 | `researcher_subgraph` | 针对单个 topic 做工具循环，最后压缩成 `compressed_research` |

关键代码在 `supervisor_tools()`：

```python
research_tasks = [
    researcher_subgraph.ainvoke({
        "researcher_messages": [HumanMessage(content=tool_call["args"]["research_topic"])],
        "research_topic": tool_call["args"]["research_topic"],
    }, context=runtime.context)
    for tool_call in allowed_conduct_research_calls
]

tool_results = await asyncio.gather(*research_tasks)
```

然后把每个 researcher 的 `compressed_research` 包装回 `ToolMessage`，交给 supervisor 下一轮判断。

## 新版 API 提醒

当前依赖里 `StateGraph` 的新签名是：

```text
StateGraph(state_schema, context_schema=None, *, input_schema=None, output_schema=None, ...)
```

当前主实现和示例都使用 `input_schema` / `output_schema`。旧教程里的 `input=...`、`output=...`、`config_schema=...` 只能作为迁移阅读材料，具体对照见第 [14 章](/knowledge-notes/docs/langgraph-langchain/14-current-api-migration/)。

## 最小真实 Agent

示例文件：[06_subgraphs_and_concurrency.py](/knowledge-notes/examples/langgraph-langchain/examples/06_subgraphs_and_concurrency.py)。

示例只保留一个 researcher 子图：

```python
researcher_graph = StateGraph(
    ResearcherState,
    input_schema=ResearcherState,
    output_schema=ResearcherOutput,
)
```

父图的 `run_researchers` 节点会并发调用两次：

```python
results = await asyncio.gather(
    *(
        researcher_graph.ainvoke({"topic": topic}, context=runtime.context)
        for topic in state["topics"]
    )
)
```

每个子图内部真实调用一次模型，生成一句摘要。父图只接收 `summary` 输出，不暴露子图内部消息。

## 运行

```bash
uv run python docs/langgraph-learning/examples/06_subgraphs_and_concurrency.py
```

预期现象：

1. 输出 `子图数: 2`。
2. 输出两条 topic 对应的模型摘要。
3. 没有搜索、MCP 或工具调用。

## 常见误区

**以为子图会自动懂父图状态。** 不会。父子状态 schema 不同的时候，要在父节点里显式转换输入和输出。

**并发等于免费提速。** 不是。`asyncio.gather` 会同时发起多个模型/工具请求，速度可能更快，但费用、限流和失败面都会扩大。

**output schema 是安全红线。** 它只控制 `invoke` 返回什么字段，不等于流式输出永远隐藏内部状态；流式章节会单独讲 `output_keys` 和 subgraph state。

## 本次真实验证

已使用默认 `openai:gpt-5.5` 并发运行两个 researcher 子图。结果为：

```text
子图数: 2
- 子图隔离状态是指在 LangGraph 中让子图拥有独立的状态结构与更新逻辑，从而降低与父图的耦合并提升流程复用性与可维护性。
- 学习如何在 LangGraph 中使用 `asyncio.gather` 并发执行多个异步节点或任务以提升工作流效率。
```

本次没有触发工具、搜索或 MCP；成本来自两个并发的短模型请求。
