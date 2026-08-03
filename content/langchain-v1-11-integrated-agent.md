# 第 11 章：综合 Agent

[16_integrated_agent.py](/knowledge-notes/examples/langchain-v1/examples/16_integrated_agent.py) 组合标准 Agent 的必要部件：

1. `context_schema=UserContext` 传入经认证的 `user_id`。
2. `InMemorySaver` 以 `thread_id` 保存短期对话，`InMemoryStore` 用 `("preferences", user_id)` 保存长期语言偏好。
3. `@tool` 通过 `ToolRuntime` 读写 Store；模型只能看到工具返回的最小文本。
4. `response_format=AssistantReply` 以可 checkpoint 的 `TypedDict` 约束最终数据，`ModelCallLimitMiddleware` 约束调用次数；第 2 章另以 Pydantic 演示更强的应用边界验证。
5. `HumanInTheLoopMiddleware` 对写偏好工具暂停；示例批准一次本地 action 后继续。
6. `astream(..., stream_mode="updates")` 读取同一次恢复运行的节点更新。

这是教学组合，不是生产模板：`InMemorySaver`/`InMemoryStore` 会在进程退出后丢失；HITL action 仅操作内存；每次执行会产生少量模型费用。生产还需要持久化存储、身份认证、工具级授权、审计、限流和删除策略。

运行：

```bash
uv run python docs/langchain/examples/16_integrated_agent.py
```

项目架构选择不变：单一助理的标准工具循环可用此形态；`open_deep_research` 的多阶段研究、并发子图和报告生成仍使用 `StateGraph`。
