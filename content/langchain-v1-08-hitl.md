# 第 8 章：人在回路（HITL）

对有外部副作用的工具使用 `HumanInTheLoopMiddleware`。它在模型提出匹配工具调用后生成 LangGraph interrupt；调用方展示 action，再以 `Command(resume={"decisions": [...]})` 恢复。必须配 `checkpointer`，否则没有可恢复状态。

```python
agent = create_agent(
    model, tools=[send_message], checkpointer=InMemorySaver(),
    middleware=[HumanInTheLoopMiddleware({"send_message": True})],
)
first = await agent.ainvoke(input, config=config)
resumed = await agent.ainvoke(
    Command(resume={"decisions": [{"type": "approve"}]}), config=config
)
```

`interrupt_on` 是 `{工具名: 配置}`：`True` 允许 approve/edit/reject/respond；也可指定 `allowed_decisions` 和动态 `when`。每个 interrupt 中可能有多个 action，`decisions` 数量与顺序必须匹配。`approve` 执行原调用；`edit` 执行编辑后的参数；`reject` 生成错误 `ToolMessage`；`respond` 由人工直接提供工具结果。

本地示例 [12_hitl.py](/knowledge-notes/examples/langchain-v1/examples/12_hitl.py) 只调用内存中的 `draft_notice`，不会发送网络消息。它先断言出现 interrupt，再批准，最后确认工具确实执行。生产实现还要将审批人、时间、原参数、编辑后参数和结果记入审计系统，并在工具本身再次授权。
