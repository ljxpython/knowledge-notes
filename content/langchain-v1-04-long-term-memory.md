# 第 4 章：长期记忆与 Store

长期记忆是跨 thread 的受控数据。`Store` 挂在编译 Agent 上，工具通过 `ToolRuntime.store` 读取；namespace 必须包含已认证用户 id，避免 A 用户读到 B 用户的偏好。

```python
store = InMemoryStore()
agent = create_agent(model, tools=[remember, recall], context_schema=UserContext, store=store)
await agent.ainvoke(input, context=UserContext(user_id="u-123"))
```

| API | 参数 | 说明 |
| --- | --- | --- |
| `store.put(namespace, key, value, index=...)` | namespace 为字符串元组 | 写入；key 由应用定义，例如 `"profile"` |
| `store.get(namespace, key)` | 精确 key | 读取单个 item |
| `store.search(namespace_prefix, query=..., filter=..., limit=...)` | 前缀和检索条件 | 列出或语义检索；仅在配置索引后依赖语义能力 |

本课用 `InMemoryStore` 证明 API 和隔离逻辑；它不持久化。示例的偏好是“回答语言”，并不写真实个人资料。运行 [08_long_term_memory.py](/knowledge-notes/examples/langchain-v1/examples/08_long_term_memory.py)，它先调用 Agent 写入，再用另一个 thread 读取同一用户偏好，并断言另一用户不可见。

state 是模型可见的对话工作区；context 是可信运行依赖；Store 是服务端长期数据。只有把 Store 内容经过最小化、脱敏和任务相关筛选后，才应放入 prompt。当前项目的 `get_all_tools(configurable, runtime.store)` 已接收 Store，以支持受控的服务端能力；它并不意味着所有 state 都会自动长期保存。
