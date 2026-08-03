# 第 13 章：源码阅读练习

这一章不新增框架概念，而是把前 12 章变成可以检查的阅读能力。每题都指向当前项目真实代码；做完后再运行相应的真实 Agent 示例验证你的理解。

## 练习 1：解释一条消息怎么走到最终报告

从 [deep_researcher.py](https://github.com/ljxpython/open_deep_research/blob/main/src/open_deep_research/deep_researcher.py) 的 `clarify_with_user` 开始，按顺序写出：

```text
输入 messages
-> ClarifyWithUser
-> ResearchQuestion
-> supervisor_messages
-> ConductResearch
-> researcher_messages
-> compressed_research
-> notes
-> final_report
```

要求：每一步写出对应的 state 字段、写它的节点、消费它的节点，以及 reducer 是追加还是覆盖。

验证：运行第 [8 章](/knowledge-notes/examples/langgraph-langchain/examples/08_integrated_mini_researcher.py) 的真实 Agent 示例，给每个节点返回的 state update 打印一个键名列表。不要打印 API Key 或整段长工具输出。

## 练习 2：为什么项目有三套消息历史

比较 [state.py](https://github.com/ljxpython/open_deep_research/blob/main/src/open_deep_research/state.py) 中：

| 字段 | 归属 | 用途 |
| --- | --- | --- |
| `messages` | `AgentState` | 用户输入、澄清和最终报告 |
| `supervisor_messages` | `AgentState` / `SupervisorState` | 研究计划与 researcher 委派结果 |
| `researcher_messages` | `ResearcherState` | 单个子题的 ReAct 工具循环 |

问题：如果用同一个 `messages` 承担三种职责，最终报告 prompt 会多出什么噪声？哪个子图会误读父图上下文？

验证：运行第 [6 章](/knowledge-notes/examples/langgraph-langchain/examples/06_subgraphs_and_concurrency.py)。观察两个子图的结果是否分别回到各自的收集位置。

## 练习 3：手算 reducer 的结果

从 `override_reducer` 开始，不运行模型，写出下面更新后 `raw_notes` 的值：

```python
current = ["old"]
append = ["new"]
replace = {"type": "override", "value": ["only-this"]}
```

答案应区分：

```text
override_reducer(current, append)  -> ["old", "new"]
override_reducer(current, replace) -> ["only-this"]
```

再解释为什么 `supervisor_messages` 的初始 system prompt 必须用 override。

验证：运行第 [2 章](/knowledge-notes/examples/langgraph-langchain/examples/02_state_and_command.py) 的真实 `Command` 示例；模型调用验证路由，手算验证 reducer 的确定性语义。

## 练习 4：工具协议的最小不变量

阅读 `researcher_tools`，列出一个 `ToolMessage` 必须保留的字段：

```python
ToolMessage(
    content=observation,
    name=tool_call["name"],
    tool_call_id=tool_call["id"],
)
```

问题：

1. 为什么同一条 AIMessage 的多个 tool call 能并发执行，却仍要一一对应 `tool_call_id`？
2. `execute_tool_safely` 为什么返回错误文本而不是直接抛异常？
3. 原生 web search 为什么不在 `tools_by_name` 中再执行一遍？

验证：运行第 [4 章](/knowledge-notes/examples/langgraph-langchain/examples/04_tool_loop.py)，确认模型返回工具请求、代码执行工具、模型再根据 `ToolMessage` 完成回答这一完整闭环。

## 练习 5：定位配置覆盖问题

假设调用方传入：

```python
context = Configuration(search_api="none")
```

但程序仍在使用 Tavily。检查顺序应是：

1. `context.search_api` 是否确实为 `SearchAPI.NONE`。
2. `Configuration.from_env()` 创建 context 时是否读到了 `SEARCH_API` 环境变量。
3. `get_all_tools(context, store)` 如何使用 `search_api`。
4. `get_search_tool` 返回了哪些工具。

验证：先执行第 11 章的最小配置检查，再运行第 [5 章](/knowledge-notes/examples/langgraph-langchain/examples/05_search_and_mcp.py)。后者只装配并调用 `think_tool`，不会触发真实搜索。

## 练习 6：画出异常传播边界

给下列函数标注“异常继续抛出”“转换为文本工具结果”“降级为原文”“结束图”：

| 函数 | 预期答案 |
| --- | --- |
| `execute_tool_safely` | 转换为文本工具结果 |
| `summarize_webpage` | 超时/异常降级为原文 |
| `tavily_search_async` | 继续向上抛出 |
| `supervisor_tools` | 当前代码中任意 researcher 异常会结束图 |
| `final_report_generation` | token 超限时缩短 findings；其他异常返回错误报告 |

验证：不调用外部搜索。直接阅读第 [12 章](/knowledge-notes/docs/langgraph-langchain/12-resilience-testing-and-migration/) 的对应路径，并用第 [7 章](/knowledge-notes/examples/langgraph-langchain/examples/07_persistence_streaming_observability.py) 的事件流理解“错误在哪个节点发生”。

## 练习 7：为一个修复选择正确的测试

场景 A：`override_reducer` 覆盖时没有清掉旧值。  
场景 B：researcher 超过并发上限时，overflow 的 tool call 没得到消息。  
场景 C：模型提供商更新异常类型，token 超限不再被识别。

选择测试：

| 场景 | 最小合适的验证 |
| --- | --- |
| A | 不调用模型的 reducer 单元测试 |
| B | 构造 `AIMessage.tool_calls` 的 async 子图测试，替换 researcher 子图为固定输出 |
| C | 用代表性异常对象测试 `is_token_limit_exceeded`，再做一次受控真实调用 |

原则：能由确定性输入验证的问题，不要消耗真实模型预算；涉及模型协议、工具回填或提供商响应时，再用章节中的真实 Agent 调用补验证。

## 完成标准

你可以不看提示，解释：

1. 为什么 `AgentState`、`SupervisorState`、`ResearcherState` 不合并。
2. `Command` 如何同时改变状态与控制流。
3. 模型调用、搜索调用、MCP 调用分别由谁付费、谁执行、谁负责权限。
4. 一个 token-limit 异常最终在哪些节点可能被截断、降级或终止。

能回答这四题后，当前项目涉及的核心 LangGraph/LangChain 知识已经完整覆盖；下一阶段再向人机中断、长期记忆、人工审批、部署和生产评估扩展。
