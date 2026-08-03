# 第 3 章：短期记忆

短期记忆是同一对话 thread 的 Agent state 持久化，不是模型自己的记忆。给 `create_agent` 传 `checkpointer=InMemorySaver()`，每次调用传相同 `config={"configurable": {"thread_id": "..."}}`，第二轮就会恢复第一轮写入的 `messages` 和中间工具消息。

```python
agent = create_agent(model, tools=[...], checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "lesson-memory-1"}}
await agent.ainvoke({"messages": [("user", "我叫小王")]}, config=config)
await agent.ainvoke({"messages": [("user", "我叫什么？")]}, config=config)
```

| 项目 | 边界 |
| --- | --- |
| state / checkpoint | 当前 thread 的 messages、工具调用、结构化结果；可恢复、可检查 |
| `thread_id` | checkpoint 的会话键，必须稳定且由服务端授权，不能直接信任任意客户端值 |
| context | 本次运行依赖；不会因 `thread_id` 自动持久化 |
| Store | 跨 thread 长期数据；不是短期聊天历史的替代品 |

`InMemorySaver` 仅适合本地学习和测试，进程退出即丢失。生产选择持久 checkpointer 并制定删除/保留策略。运行 [07_short_term_memory.py](/knowledge-notes/examples/langchain-v1/examples/07_short_term_memory.py) 会发起两次短模型调用；第二次的问题必须引用第一轮名称。

当前项目第 7 章讲解同一机制。`deep_researcher` 的 `messages` 属于 `AgentState`，调用方可用 thread config 恢复执行；`Configuration` 属于 `Runtime.context`，不应改放 checkpoint。
