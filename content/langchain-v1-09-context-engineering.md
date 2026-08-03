# 第 9 章：Context engineering

Context engineering 是把有限、可信、任务相关的信息在正确时机交给模型，不是把所有数据拼进 system prompt。一个可审查顺序是：稳定规则 -> 最近消息 -> 已验证工具结果 -> 当前任务所需的最小长期记忆 -> 模型调用。

| 来源 | 生命周期 | 给模型的规则 |
| --- | --- | --- |
| system prompt | Agent 定义期 | 只放稳定策略和安全约束 |
| messages | thread 内 | 保留近期事实；用 checkpoint、裁剪或摘要控制增长 |
| ToolMessage | 一次工具调用 | 只回填与当前任务有关的受控输出 |
| `Runtime.context` | 单次运行 | 默认不给模型；middleware/工具按需投影最小字段 |
| Store | 跨 thread | 用用户 namespace 检索、脱敏、限量后才写入消息 |

`context_schema` 定义 `Runtime.context` 的类型，调用时 `agent.ainvoke(input, context=UserContext(...))`。它特别适合 `user_id`、权限、连接等可信依赖；不要用它塞聊天记录，也不要把 `RunnableConfig` 当业务 context。当前项目以 `Runtime[Configuration]` 读取模型选择、用户身份和密钥，其代码位置是 `deep_researcher.py` 的各节点。

上下文预算的优先级：删除重复工具输出，再裁剪低价值旧消息，再使用 `SummarizationMiddleware`，最后才升级模型上下文窗口。摘要会丢失细节，原始证据要保存在可检索的受控存储中。运行 [13_context_boundaries.py](/knowledge-notes/examples/langchain-v1/examples/13_context_boundaries.py) 进行本地断言，证明 context 不会自动出现在 `messages`。
