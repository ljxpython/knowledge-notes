# 第 4 章：工具循环

## 学习目标

看懂当前项目最核心的 Agent 闭环：模型决定是否调用工具，代码执行工具，把结果包装成 `ToolMessage`，再把消息历史交还给模型继续推理。

## 它是什么

`@tool` 把 Python 函数暴露成模型可调用工具。`bind_tools(tools)` 把这些工具 schema 绑定到模型。若模型选择调用工具，返回的 `AIMessage` 会带 `tool_calls`；你必须执行这些调用，并为每个调用构造一个 `ToolMessage`，其中 `tool_call_id` 必须匹配原来的调用 id。这个机制解决“模型知道何时该找外部能力，而不是硬编答案”的问题。

## 当前项目怎么用

当前仓库没有用 `ToolNode`，而是手写工具循环：

| 阶段 | 当前代码 |
| --- | --- |
| 绑定工具 | `supervisor()` 里 `configurable_model.bind_tools([...])`；`researcher()` 里 `configurable_model.bind_tools(tools)` |
| 读取工具调用 | `supervisor_tools()` / `researcher_tools()` 读 `most_recent_message.tool_calls` |
| 执行工具 | `researcher_tools()` 里 `await tool.ainvoke(args, config)`；支持 `asyncio.gather` 并行 |
| 写回结果 | 构造 `ToolMessage(content=..., name=..., tool_call_id=...)` |
| 回到模型 | `goto="supervisor"` 或 `goto="researcher"` 继续下一轮 |

这就是标准 ReAct 的最小骨架，只是项目把研究任务和 MCP 工具一起放进这个循环里了。

## 最小真实 Agent

示例文件：[04_tool_loop.py](/knowledge-notes/examples/langgraph-langchain/examples/04_tool_loop.py)。

示例只保留一个工具：

```python
@tool
def multiply_by_two(value: int) -> str:
    """Multiply the input integer by two."""
    return str(value * 2)
```

图只有两个节点：

1. `agent`：真实模型 + `bind_tools([multiply_by_two])`
2. `run_tools`：读取 `AIMessage.tool_calls`，执行工具并生成 `ToolMessage`

如果模型没有工具调用，就结束；如果有，就回到 `agent` 再让模型基于工具结果给最终答案。

## 运行

```bash
uv run python docs/langgraph-learning/examples/04_tool_loop.py
```

预期现象：

1. 第一轮模型为了解题发出工具调用。
2. `run_tools` 执行工具，把结果作为 `ToolMessage` 追加回消息历史。
3. 第二轮模型读取工具结果，输出最终自然语言答案。

## 常见误区

**工具返回值直接 print 就完了。** 不行，模型看不到你的终端输出；必须把结果包装成 `ToolMessage` 放回消息历史。

**`tool_call_id` 随便填。** 不行，必须与对应 `AIMessage.tool_calls[i]["id"]` 一致，否则模型无法把哪条工具结果对应到哪次调用。

**工具循环一定要框架预构建。** 不一定。当前项目就是手写循环，这样你更容易理解每一步状态变化；后面扩展时再对比 `ToolNode`。

## 本次真实验证

已使用默认 `openai:gpt-5.5` 运行一次。结果为：

```text
消息数: 4
最终答复: 21 的两倍是 42。
```

`消息数: 4` 对应最小工具循环的四个协议消息：用户消息、带 `tool_calls` 的模型消息、`ToolMessage`、最终模型答复。
