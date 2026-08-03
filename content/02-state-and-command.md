# 第 2 章：状态与动态路由

## 学习目标

理解 LangGraph 里“状态如何保存”和“节点下一步去哪”是两件独立但协作的事：`StateGraph` 定义状态、节点和固定边；节点返回 `Command` 才能同时更新状态并动态指定下一跳。

## 它是什么

`MessagesState` 是对话型状态的快捷基类，自带 `messages` 和专门处理消息追加、更新的 reducer。`TypedDict` 适合纯内部状态；`Annotated[T, reducer]` 为某个字段指定合并规则。`Command(update=..., goto=...)` 适合节点既要写状态又要按本轮结果决定下一个节点的场景。

## 当前项目怎么用

| 概念 | 当前项目位置 | 职责 |
| --- | --- | --- |
| `AgentState(MessagesState)` | `src/open_deep_research/state.py` | 外层图保存用户、模型与最终报告消息。 |
| `SupervisorState`、`ResearcherState` | `src/open_deep_research/state.py` | 子图内部的轻量任务状态。 |
| `Annotated[..., operator.add]` | `ResearcherState.researcher_messages` | 每轮追加模型回复和工具回复。 |
| `override_reducer` | `AgentState.notes` 等字段 | 默认追加，指定 `{"type": "override"}` 时整体替换。 |
| `StateGraph(...)` | `src/open_deep_research/deep_researcher.py` | 分别构建外层、supervisor、researcher 三张图。 |
| `Command` | `clarify_with_user()`、`supervisor_tools()`、`researcher_tools()` | 根据状态和本轮模型/工具结果更新状态并跳转。 |

项目中的 `researcher()` 是完整范式：

```python
return Command(
    goto="researcher_tools",
    update={
        "researcher_messages": [response],
        "tool_call_iterations": state.get("tool_call_iterations", 0) + 1,
    },
)
```

这里 `response` 会被 `operator.add` 追加到历史；下一轮节点则由 `goto` 指向 `researcher_tools`。

## 最小真实 Agent

示例文件：[02_state_and_command.py](/knowledge-notes/examples/langgraph-langchain/examples/02_state_and_command.py)。

```python
class LearningState(MessagesState):
    route_log: Annotated[list[str], operator.add]
```

它继承 `MessagesState`，再增加一个自定义字段。模型节点返回：

```python
return Command(
    update={
        "messages": [response],
        "route_log": ["answer -> finish"],
    },
    goto="finish",
)
```

`messages` 由内置消息 reducer 合并，`route_log` 由 `operator.add` 合并。`finish` 节点没有调用模型，只追加第二条路由记录，然后沿静态边结束。

## `MessagesState`、`TypedDict` 怎么选

| 状态内容 | 选型 | 本项目例子 |
| --- | --- | --- |
| 多轮消息是主要上下文 | `MessagesState` | `AgentState`。 |
| 只存任务字段、计数器、笔记 | `TypedDict` | `SupervisorState`、`ResearcherState`。 |
| 某个字段要累积或自定义合并 | `Annotated[..., reducer]` | `researcher_messages`、`notes`。 |

`TypedDict` 只描述字典形状，不做 Pydantic 式运行时校验；模型输出和工具参数需要校验时，下一章会使用 `BaseModel` 与 `Field`。

## 运行

```bash
uv run python docs/langgraph-learning/examples/02_state_and_command.py
```

预期现象：

1. 模型只被调用一次。
2. 最终 `messages` 有两条消息：输入的 `HumanMessage` 与输出的 `AIMessage`。
3. `route_log` 依次输出 `answer -> finish`、`finish -> END`。

## 常见误区

**把静态边和 `Command.goto` 同时从同一节点指向不同节点。** 静态 `add_edge` 仍会执行；需要动态跳转的节点应只用 `Command` 控制下一跳。本例从 `answer` 不添加静态出边，只让 `Command` 选择 `finish`。

**以为 `Annotated` 自己会追加列表。** 它只是把 reducer 元数据放在类型上；真正执行合并的是 LangGraph。没有 reducer 的字段默认按覆盖语义更新。

**把 `Command` 和 `Command(resume=...)` 混为一谈。** 本章的 `goto` 是图内路由；`resume` 用于配合 `interrupt()` 恢复暂停中的图，留到持久化与人工介入章节。

## 本次真实验证

已使用默认 `openai:gpt-5.5` 运行一次。结果为：

```text
消息数: 2
路由: answer -> finish | finish -> END
答复: 状态机适合 Agent，因为它能把复杂行为拆成清晰的状态与转移规则，使 Agent 在不同情境下稳定、可控地决策和执行。
```
