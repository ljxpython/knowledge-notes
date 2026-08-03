# 第 10 章：从用户问题到最终报告的完整链路

这一章只追踪当前主实现，不重新发明一个“教学版架构”。源码入口是 [deep_researcher.py](https://github.com/ljxpython/open_deep_research/blob/main/src/open_deep_research/deep_researcher.py) 中编译出的 `deep_researcher`。

## 1. 主图是编排层，不是所有工作都在一个节点里

```python
deep_researcher_builder = StateGraph(
    AgentState,
    input_schema=AgentInputState,
)
```

`AgentInputState` 只公开 `messages`。主图内部使用扩展后的 `AgentState` 保存研究简报、supervisor 对话、笔记和最终报告。这样调用方只需传入用户消息，内部字段不会成为公共输入契约。

图的固定边是：

```text
START -> clarify_with_user
clarify_with_user --Command--> write_research_brief 或 END
write_research_brief --Command--> research_supervisor
research_supervisor -> final_report_generation -> END
```

`clarify_with_user` 和 `write_research_brief` 返回 `Command`，因此跳转不是由 `add_conditional_edges` 声明，而是由节点在运行时选择。

## 2. 澄清阶段：先判断，不要直接研究

`clarify_with_user` 用 `ClarifyWithUser` Pydantic 模型做结构化输出：

```python
class ClarifyWithUser(BaseModel):
    need_clarification: bool
    question: str
    verification: str
```

当 `allow_clarification=False`，节点直接返回 `Command(goto="write_research_brief")`，不会请求模型。否则它调用：

```python
configurable_model.with_structured_output(ClarifyWithUser)
```

这一步的要点不是“模型会不会聊天”，而是把分支条件转成类型化数据。模型认为信息不够时，图以 `END` 结束并把问题作为 `AIMessage` 写入 `messages`；下一轮用户补充后，再从入口重新执行。

真实调用对应第 [3 章](/knowledge-notes/docs/langgraph-langchain/03-structured-output/) 的结构化输出和第 [2 章](/knowledge-notes/docs/langgraph-langchain/02-state-and-command/) 的 `Command` 路由。

## 3. 简报阶段：把对话压成可委派任务

`write_research_brief` 将所有用户消息格式化后，要求模型返回唯一的 `research_brief`。然后它覆盖 `supervisor_messages`：

```python
{
    "type": "override",
    "value": [
        SystemMessage(content=supervisor_system_prompt),
        HumanMessage(content=response.research_brief),
    ],
}
```

这里必须覆盖，而不是追加。`supervisor_messages` 是一个新的角色对话，它不应携带用户澄清过程里所有原始来回消息；保留原始用户消息的是 `AgentState.messages`。

## 4. supervisor 子图：决定研究拆分

主图把 `supervisor_subgraph` 作为 `research_supervisor` 节点。子图 state 是 `SupervisorState`，它的循环是：

```text
START -> supervisor -> supervisor_tools --Command--> supervisor 或 END
```

`supervisor` 将三个工具绑定给研究模型：

| 工具 | 作用 |
| --- | --- |
| `think_tool` | 记录推理后的研究策略 |
| `ConductResearch` | 给某个子主题创建 researcher 工作 |
| `ResearchComplete` | 显式结束研究阶段 |

`supervisor_tools` 还会在无工具调用、调用 `ResearchComplete`、或超过 `max_researcher_iterations` 时结束。结束时通过 `get_notes_from_tool_calls` 把收到的 researcher 压缩结果取为主图的 `notes`。

## 5. 并发 researcher：模型提出任务，代码施加上限

对于每个 `ConductResearch`，`supervisor_tools` 调用：

```python
researcher_subgraph.ainvoke({...}, context=runtime.context)
```

它将前 `max_concurrent_research_units` 个任务放进 `asyncio.gather`。超过上限的工具调用得到一条 `ToolMessage` 错误说明，而不是偷偷丢掉。

这体现了 Agent 的职责边界：

- 模型负责提出“该研究哪些子题”。
- 应用代码负责并发、预算、超时和资源上限。

真实并发 Agent 调用见第 [6 章](/knowledge-notes/docs/langgraph-langchain/06-subgraphs-and-concurrency/)。

## 6. researcher 子图：标准 ReAct 循环

researcher 的 state 独立于 supervisor：

```text
START -> researcher -> researcher_tools
researcher_tools --Command--> researcher 或 compress_research
compress_research -> END
```

`researcher` 通过 `get_all_tools(runtime.context, runtime.store)` 动态获得：

1. 始终有 `ResearchComplete` 与 `think_tool`。
2. 按 `search_api` 增加 Tavily 或模型提供商原生 web search。
3. 按 MCP 配置增加远程工具。

`researcher_tools` 用 `asyncio.gather` 并行执行一条 AI 消息中的普通工具调用，并把结果逐个转成 `ToolMessage`。若模型没有发起工具调用、已调用 `ResearchComplete`，或超过 `max_react_tool_calls`，才进入压缩。

原生 OpenAI/Anthropic web search 是例外：搜索执行在模型提供商侧，项目通过 response metadata 检测它是否发生，而不会重复当成本地工具执行。

真实工具协议调用见第 [4 章](/knowledge-notes/docs/langgraph-langchain/04-tool-loop/)，工具装配见第 [5 章](/knowledge-notes/docs/langgraph-langchain/05-search-and-mcp/)。

## 7. 压缩和写作：两次不同职责的模型调用

`compress_research` 是 researcher 子图的出口。它读取 researcher 工具与 AI 消息，生成 `compressed_research`，并保留可审计的 `raw_notes`。

最后 `final_report_generation`：

1. 拼接 supervisor 收集的 `notes`。
2. 使用 `final_report_model` 生成 `final_report`。
3. 用 override 将 `notes` 清空，避免最终 checkpoint 无意义地重复存大段内容。
4. 把最终回复作为 `AIMessage` 写进主 `messages`。

“压缩研究”和“写最终报告”不能随意合并：前者面对单个子题的长工具记录，后者面对跨子题的已压缩证据，两者的 token 预算和 prompt 目标不同。

## 8. 用一条真实调用把流程串起来

第 [8 章](/knowledge-notes/docs/langgraph-langchain/08-integrated-mini-researcher/) 已对同样的图模式做过一次真实模型调用验证。要运行完整项目图，应先显式关闭搜索以避免产生外部搜索费用，并提供模型密钥：

```python
result = await deep_researcher.ainvoke(
    {"messages": [HumanMessage(content="比较两个技术方案的关键取舍。")]},
    context=Configuration(
        allow_clarification=False,
        search_api="none",
        max_concurrent_research_units=1,
        max_researcher_iterations=1,
        max_react_tool_calls=1,
    ),
)
print(result["final_report"])
```

这仍会触发多次模型调用，且模型可能选择提前结束研究。它适合手动学习，不作为每次本地测试必跑项。

## 9. 读图练习

拿一条 `ConductResearch` 工具调用，写出它的数据变化：

```text
AIMessage.tool_calls
  -> supervisor_tools
  -> researcher_subgraph 输入 researcher_messages/research_topic
  -> compress_research 输出 compressed_research/raw_notes
  -> ToolMessage 写回 supervisor_messages
  -> get_notes_from_tool_calls 写入主 AgentState.notes
  -> final_report_generation 消费 notes
```

能把这条链讲清楚，才算真正读懂本项目的 Agent 协作。
