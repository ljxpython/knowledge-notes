# 第 8 章：综合迷你研究员

## 学习目标

把前 7 章串成一个不联网的 mini deep researcher：输入用户问题，生成结构化研究计划，并发调用 researcher 子图，每个 researcher 跑一次本地工具循环，最后汇总成报告，并用 checkpointer 保存线程状态。

## 它是什么

这个综合案例不是新概念，而是把项目主线缩小到能一次看懂的版本。它对应当前项目的骨架：外层图负责 planning 和 final report，researcher 子图负责单个 topic，父图用 `asyncio.gather` 并发调用多个 researcher。为了安全和省钱，示例不调用搜索、不连接 MCP，只用本地工具模拟“研究中记录边界”。

## 知识点对应关系

| 前面章节 | 综合案例位置 | 项目对应 |
| --- | --- | --- |
| 真实模型与消息 | 所有模型节点都用 `HumanMessage` 和真实 `ainvoke` | `researcher()`、`final_report_generation()` |
| 状态与路由 | 节点返回 `Command(update=..., goto=...)` | `clarify_with_user()`、`researcher_tools()` |
| 结构化输出 | `make_plan` 返回 `MiniPlan` | `write_research_brief()` 返回 `ResearchQuestion` |
| 工具循环 | researcher 子图绑定 `record_learning_boundary` | `researcher()` 绑定搜索/MCP/think 工具 |
| 搜索与 MCP | 明确不联网，只保留工具装配协议 | `get_all_tools()` |
| 子图与并发 | 父图 `asyncio.gather` 调两个 researcher 子图 | `supervisor_tools()` |
| 持久化与观测 | `InMemorySaver`、`thread_id`、`astream_events`、`get_state` | 部署时的 checkpointer / LangSmith 观测 |

## 最小真实 Agent

示例文件：[08_integrated_mini_researcher.py](/knowledge-notes/examples/langgraph-langchain/examples/08_integrated_mini_researcher.py)。

流程：

```text
START
  -> make_plan
  -> run_researchers
       -> researcher_graph(topic A)
       -> researcher_graph(topic B)
  -> write_final
  -> END
```

researcher 子图内部：

```text
researcher_agent
  -> researcher_tools
  -> researcher_agent
  -> END
```

第一轮 researcher 模型被强制调用本地工具 `record_learning_boundary`；第二轮模型读取 `ToolMessage` 后生成一句摘要。

## 运行

```bash
uv run python docs/langgraph-learning/examples/08_integrated_mini_researcher.py
```

预期现象：

1. 输出事件数。
2. 输出结构化计划产生的两个 topic。
3. 输出两个 researcher 摘要。
4. 输出最终报告。
5. 输出持久化状态中的消息数。

## 常见误区

**把综合案例当生产版 deep research。** 不是。它是学习版，刻意去掉搜索、MCP、长报告、错误重试和 token 截断。

**以为子图并发只要套 `gather` 就完了。** 不够。父图必须把父状态转换成子图输入，再把子图输出转换回父状态；真实项目还要处理限流、失败和部分结果。

**以为本地工具等价于搜索/MCP。** 不等价。本地工具只验证工具协议；真实搜索/MCP 的认证、权限、网络失败和费用边界要单独验证。

## 本次真实验证

已使用默认 `openai:gpt-5.5` 运行一次。结果为：

```text
事件数: 675
主题: open_deep_research 中的 LangGraph 工具循环：研究 Agent 如何在模型调用、工具调用、观察结果与继续/结束判断之间循环执行 | open_deep_research 中的子图并发模式：如何拆分多个研究子任务、并行运行子图并汇总结果
路由: make_plan -> run_researchers | run_researchers -> write_final | write_final -> END
摘要数: 2
最终报告: open_deep_research 展示了用 LangGraph 构建研究型 Agent 的核心模式：通过状态 schema 记录研究问题、消息历史、工具观察、阶段性摘要与最终输出，并由节点定义模型推理、工具执行、总结聚合等步骤。
其工具循环采用“LLM 决定下一步或发起工具调用 → 工具节点执行搜索/抓取/分析并写回状态 → 条件边判断继续检索、进入总结或终止”的状态流转，使研究过程能在信息不足时持续迭代，在达到轮次上限、无新工具调用或结果充分时结束。
子图并发则将复杂主题拆成多个独立研究任务，并行运行相同研究子图，最后汇总成功结果、处理失败或缺失输出并生成综合报告；这一模式可迁移到自己的 LangGraph 应用中，用于多主题搜索、并行分析和结构化结果聚合。
持久化消息数: 2
```

运行时出现两个告警：

- `v3 streaming protocol on Pregel is experimental`：当前版本的 v3 事件流仍是 beta。
- `PydanticSerializationUnexpectedValue`：事件流序列化结构化输出对象时的提示，不影响最终状态。

本次没有触发搜索、MCP 或生产 API；成本来自 plan、两个并发 researcher 工具循环和 final report 的短模型调用。
