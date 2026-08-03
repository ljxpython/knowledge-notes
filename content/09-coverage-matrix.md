# 第 9 章：项目知识覆盖矩阵

前 8 章按 LangGraph/LangChain 的核心 API 递进讲解。本章把这些概念重新映射到 `src/open_deep_research`，目的是避免“会写一个 demo，却看不懂项目为什么这样组合”。

## 先看全局

```text
用户 messages
  -> clarify_with_user
  -> write_research_brief
  -> supervisor 子图
       -> 0..N 个 researcher 子图（并发）
       -> 汇总 notes
  -> final_report_generation
  -> final_report
```

主图定义在 [deep_researcher.py](https://github.com/ljxpython/open_deep_research/blob/main/src/open_deep_research/deep_researcher.py)，主状态定义在 [state.py](https://github.com/ljxpython/open_deep_research/blob/main/src/open_deep_research/state.py)，运行期选择由 [configuration.py](https://github.com/ljxpython/open_deep_research/blob/main/src/open_deep_research/configuration.py) 提供。

## 覆盖表

| 项目中的问题 | 实际类型或 API | 阅读位置 | 已验证的真实 Agent 示例 | 学习时要回答的问题 |
| --- | --- | --- | --- | --- |
| 用户消息怎样累计 | `MessagesState`、`messages` reducer | `AgentInputState`、`AgentState` | [01](/knowledge-notes/examples/langgraph-langchain/examples/01_real_model_agent.py) | 为什么节点只返回新消息而不是整段历史？ |
| 非消息状态怎样合并 | `TypedDict`、`Annotated`、`operator.add`、自定义 reducer | `AgentState`、`SupervisorState`、`ResearcherState` | [02](/knowledge-notes/examples/langgraph-langchain/examples/02_state_and_command.py) | 这个字段是追加、覆盖，还是最后写入者获胜？ |
| 模型如何产生可控决策 | `BaseModel`、`Field`、`with_structured_output` | `ClarifyWithUser`、`ResearchQuestion` | [03](/knowledge-notes/examples/langgraph-langchain/examples/03_structured_output.py) | 这里为什么不用让模型直接输出 JSON 文本？ |
| 模型如何请求外部动作 | `@tool`、`bind_tools`、`ToolMessage` | `think_tool`、`ConductResearch`、`ResearchComplete` | [04](/knowledge-notes/examples/langgraph-langchain/examples/04_tool_loop.py) | 工具调用结果为什么必须回填为同一个 `tool_call_id`？ |
| 运行时下一跳如何决定 | `Command(goto=..., update=...)` | `clarify_with_user`、两个 tool 节点 | [02](/knowledge-notes/examples/langgraph-langchain/examples/02_state_and_command.py) | `goto` 与 `update` 为什么要在一次返回中同时出现？ |
| 搜索与外部工具如何装配 | Tavily、原生 web search、MCP | `get_all_tools`、`get_search_tool`、`load_mcp_tools` | [05](/knowledge-notes/examples/langgraph-langchain/examples/05_search_and_mcp.py) | 哪些工具运行在模型侧，哪些由本地代码执行？ |
| 研究任务为什么可并发 | 子图、`asyncio.gather` | `supervisor_tools` | [06](/knowledge-notes/examples/langgraph-langchain/examples/06_subgraphs_and_concurrency.py) | 并发上限放在哪里，为什么不完全交给模型？ |
| 状态如何跨请求保存和观察 | checkpointer、`thread_id`、事件流 | LangGraph 平台运行时与第 7 章 | [07](/knowledge-notes/examples/langgraph-langchain/examples/07_persistence_streaming_observability.py) | `thread_id` 与“用户身份”是不是一回事？ |
| 小型完整工作流如何拼装 | `StateGraph`、工具循环、汇总节点 | 第 8 章的 mini researcher | [08](/knowledge-notes/examples/langgraph-langchain/examples/08_integrated_mini_researcher.py) | 哪些部分可复用，哪些必须按业务重写？ |
| 当前项目完整链路 | 主图 + supervisor/researcher 子图 | 本章后续第 10 章 | 第 1–8 章组合验证 | 每次 `Command` 写了什么状态，谁消费它？ |
| 主/子 agent 如何交接信息 | `input_schema`、`output_schema`、Pydantic handoff model、显式 state 投影 | `supervisor_tools`、`ResearcherOutputState` | [15](/knowledge-notes/examples/langgraph-langchain/examples/10_multi_agent_handoff.py) | 用户问题、任务和结果为何不能共用一份无约束 dict？ |
| 配置、密钥、MCP 登录 | `Runtime.context`、Pydantic、`RunnableConfig` 控制面、LangGraph Store | `configuration.py`、`utils.py` | 第 5、7 章的真实调用锚点 | 配置和密钥分别从哪来，谁能看到？ |
| 失败恢复和评估 | retry、token 截断、`pytest`、LangSmith evaluation | `utils.py`、`tests/` | 第 6、7 章的运行锚点 | 哪些异常应该终止，哪些应该降级？ |

## 三种运行数据不要混淆

1. **Graph state**：一次图执行中被节点读写的数据，例如 `notes`、`research_brief`、`researcher_messages`。它是工作流的短期记忆。
2. **Runtime context**：一次运行的业务上下文，例如 `research_model`、`search_api`、并发上限。它通过 `context_schema` 和 `context=` 传入，节点从 `runtime.context` 读取；它也不是图状态。
3. **RunnableConfig**：一次调用的运行控制参数，例如 `tags`、callbacks、recursion limit、`thread_id`。它不承载本项目业务配置，节点也不会自动把它写进 checkpoint。
4. **Store 中的持久数据**：本项目用于保存 MCP access token，按 `(user_id, "tokens")` 命名空间隔离。它不应混入 `AgentState` 或 prompt。

第 7 章里同一个 `thread_id` 可恢复图状态；第 11 章会说明它仍不能代替认证用户的 `owner`。

## 版本差异提醒

当前项目的构图参数已迁移为当前命名：

```python
StateGraph(AgentState, input_schema=AgentInputState)
```

当前 Python 文档推荐显式使用 `input_schema`、`output_schema` 和 `context_schema`。本项目主图和学习示例均已使用这三个入口；`context_schema` 的完整迁移原因放在第 14 章。

参考：LangGraph 官方 Python Graph API 的“multiple schemas”和“input/output schemas”章节。

## 本章检查

回答下面四题，再进入下一章：

1. `researcher_messages` 追加一条 `ToolMessage` 时，谁决定“追加”而不是覆盖？
2. `runtime.context` 为什么不应该写回 `AgentState`？为什么业务配置不应放入 `RunnableConfig`？
3. `ResearcherOutputState` 为什么只暴露压缩结果和原始笔记，而不暴露整个工具对话？
4. `messages` 和 `supervisor_messages` 为什么必须是两个不同的字段？
# LangChain Agent 扩展覆盖

LangChain v1 的标准 Agent 课程位于 [langchain/README.md](/knowledge-notes/collections/langchain-v1/)。它与主项目的取舍如下：

| 需求 | 首选 | 当前项目证据 | 原因 |
| --- | --- | --- | --- |
| 一个模型加有限工具的标准 ReAct 循环 | `create_agent` | `researcher -> researcher_tools` 是同类手写循环 | 框架维护 `AIMessage -> ToolMessage` 循环，少写样板代码 |
| 结构化最终答复、记忆、流式、审批 | `create_agent` + 参数/middleware | 主图有结构化输出、checkpoint、事件流，但未使用 Agent middleware | 标准能力可以独立学习后用于简单助理 |
| 澄清、研究 brief、supervisor、多 researcher 并发、压缩、报告 | `StateGraph` | `deep_researcher.py` 的 main/supervisor/researcher 三层图 | 需要显式节点、子图、state 契约和可审查路由，不能压成单 Agent |
| 自动子 Agent 委派 | 先用 compiled subgraph；`deepagents` 为可选扩展 | `supervisor_subgraph`、`researcher_subgraph` | `deepagents` 非当前依赖，不能假装已使用 |

这不是“LangChain 或 LangGraph 二选一”：`create_agent` 本身返回 `CompiledStateGraph`。区别在于谁定义运行图，标准循环由 LangChain 预制，复杂业务编排由应用显式编写。
