# 第 1 章：构造 `create_agent`

## 目标

`create_agent` 是 LangChain v1 推荐的标准 Agent 入口。它返回 `CompiledStateGraph`：模型先看 state 中的 `messages`，若输出 `AIMessage.tool_calls`，框架运行对应工具，按同一调用 id 回填 `ToolMessage`，再调用模型；直到模型不再请求工具。它不是“脱离 LangGraph”的黑盒，而是替你写好标准循环。

```python
agent = create_agent(model, tools=[multiply], system_prompt="...", response_format=Answer)
result = await agent.ainvoke({"messages": [{"role": "user", "content": "23 * 7"}]})
```

## 核心签名和选型

| 参数 | 作用 | 何时使用 |
| --- | --- | --- |
| `model` | 模型名或 `BaseChatModel` | 必填；模型必须支持所需工具/结构化能力 |
| `tools` | 函数、`@tool` 或 `BaseTool` 序列 | 让模型能执行外部受控动作；无工具可为 `None` |
| `system_prompt` | `str` 或 `SystemMessage` | 稳定角色、工具约束和输出原则 |
| `response_format` | Pydantic、dataclass、TypedDict 或 provider/tool strategy | 需要机器可读的最终答复 |
| `middleware` | `AgentMiddleware` 序列 | 限制、摘要、审批、动态模型等横切策略 |
| `state_schema` | 自定义 Agent state 类型 | 标准 `messages` 之外确有运行中字段时 |
| `context_schema` | `Runtime.context` 的类型 | 为工具/中间件提供本次可信依赖 |
| `checkpointer` | checkpoint 实现 | 多轮短期记忆、HITL resume |
| `store` | `BaseStore` | 跨 thread 的长期记忆 |
| `interrupt_before` / `interrupt_after` | 图节点名列表 | 调试或显式人工暂停；业务审批优先使用 HITL middleware |
| `debug`、`name`、`cache`、`transformers` | 调试、命名、缓存、图转换扩展 | 有明确运维或集成需求再用 |

`create_agent` 适合单模型加工具的标准循环。当前项目不能整体改成它：`src/open_deep_research/deep_researcher.py` 有澄清、研究简报、supervisor 子图、并发 researcher、压缩和最终报告，属于显式 `StateGraph` 编排。`researcher` 节点内部的循环才是可替换候选。

## 数据流

```text
输入 messages -> model -> AIMessage.tool_calls?
                         | 否 -> 最终 messages / structured_response
                         | 是 -> tools -> ToolMessage(tool_call_id) -> model
```

- state：默认 Agent state 是消息和可选 `structured_response`；它会被 checkpoint 保存。
- context：通过 `agent.ainvoke(..., context=RunContext(...))` 传入，不自动进入模型 prompt。
- Store：工具或 middleware 从 runtime 读取，跨 thread 保存；模型只看你主动写回消息的摘要。
- config：`thread_id`、tags、metadata、callbacks 是调用控制面，不应承载业务身份。

## 最小真实调用

运行 [03_create_agent.py](/knowledge-notes/examples/langchain-v1/examples/03_create_agent.py)。`multiply` 的 docstring、参数类型和 system prompt 都在帮助模型正确选工具；最终 Pydantic 结果位于 `result["structured_response"]`。

```bash
uv run python docs/langchain/examples/03_create_agent.py
```

## 常见错误

- 把复杂 supervisor 流程塞入一个 Agent：失去明确节点、并发和状态契约，继续用 `StateGraph`。
- 以为 `response_format` 验证现实事实：它只验证最终数据形状，工具结果仍应由工具层保证。
- 把 `user_id` 塞进 messages：应放 `context`，避免被模型复述和被 checkpoint 无限制复制。
