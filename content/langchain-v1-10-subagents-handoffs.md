# 第 10 章：子 Agent 与结构化交接

子 Agent 的目的不是把任何函数都拆成 Agent，而是隔离专业工具、上下文和失败边界。父 Agent 只传任务契约，子 Agent 只返结果契约，禁止把完整父对话、认证信息或所有 Store 内容直接转发。

```text
用户问题 -> 父：TaskContract(topic, constraints)
        -> 子图：只获得任务和必要 context
        -> 父：ResultContract(summary, sources, uncertainty)
        -> 最终回答
```

当前项目已经使用推荐的显式方式：`deep_researcher.py` 编译 `supervisor_subgraph` 和 `researcher_subgraph`，`ConductResearch` 定义任务，`ResearcherOutputState` 定义子图输出，supervisor 汇总 `compressed_research`。这需要并发、压缩和明确 state，所以继续用 LangGraph compiled subgraph，而不是强行嵌入 `create_agent`。

`deepagents` 的 `SubAgentMiddleware` 是额外包的可选扩展，不是 LangChain core，也不在本仓库依赖中。本课不安装它；需要其自动委派能力时，应单独评估隔离、成本、可观测性和版本兼容性。运行 [15_structured_handoff.py](/knowledge-notes/examples/langchain-v1/examples/15_structured_handoff.py) 会以 Pydantic `TaskContract`/`ResultContract` 验证最小父子图契约；该示例不联网。
