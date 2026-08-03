# 第 2 章：消息、Prompt、工具与结构化输出

## 消息协议

| 类型 | 谁创建 | 关键字段 | 用途 |
| --- | --- | --- | --- |
| `SystemMessage` | 应用 | `content` | 稳定行为约束；通常由 `system_prompt` 注入 |
| `HumanMessage` | 用户/应用 | `content`、可选 `name` | 用户意图 |
| `AIMessage` | 模型 | `content`、`tool_calls`、`usage_metadata` | 模型文字或工具请求 |
| `ToolMessage` | 工具运行器 | `content`、`name`、`tool_call_id`、`status` | 对某一次工具调用的结果 |

最重要的协议约束是：每个 `ToolMessage.tool_call_id` 必须等于触发它的 `AIMessage.tool_calls[i]["id"]`。模型借此把结果和调用对应起来；漏掉或写错 id 会使对话历史不合法。运行 [04_message_protocol.py](/knowledge-notes/examples/langchain-v1/examples/04_message_protocol.py) 可看到本地断言。

## Prompt

`ChatPromptTemplate` 在 Agent 外更常用于固定链；在 Agent 内优先用 `system_prompt`，再把动态的、已授权的信息作为消息或 middleware 处理。

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是{role}"),
    MessagesPlaceholder("history", optional=True),
    ("human", "{question}"),
]).partial(role="助手")
messages = prompt.invoke({"question": "解释 reducer"}).messages
```

`from_messages` 接受消息模板列表；`MessagesPlaceholder(variable_name, optional=False, n_messages=None)` 插入已有历史，`n_messages` 是展示预算，不是安全脱敏。

## 工具

`@tool` 从函数名、docstring、类型注解创建 schema。参数必须具体、可序列化；docstring 要描述何时调用和副作用。`ToolRuntime` 注入参数不会暴露给模型，可读取 `runtime.context`、`runtime.store` 和当前 tool call id。

```python
@tool
def lookup_preference(runtime: ToolRuntime) -> str:
    """Return the current user's saved preference."""
    item = runtime.store.get(("preferences", runtime.context.user_id), "profile")
    return str(item.value if item else {})
```

工具实现是信任边界：验证输入、授权用户、限制副作用；不要相信模型生成的参数。

## 结构化输出

```python
class Answer(BaseModel):
    result: int = Field(description="精确结果")
    explanation: str = Field(min_length=1, description="一句中文说明")

agent = create_agent(model, tools=[multiply], response_format=Answer)
answer: Answer = (await agent.ainvoke(input))["structured_response"]
```

`Field` 用于默认值、验证约束和给模型的字段语义；`BaseModel` 在应用边界验证类型。不要在 `messages` 中手工解析 JSON 来代替 `response_format`。当 provider 原生结构化输出可用时，框架使用它；否则会使用 tool strategy，调用轨迹可能多一轮。

当前项目的 `ClarifyWithUser`、`ResearchQuestion`、`ConductResearch` 位于 `src/open_deep_research/state.py`：前两个用于 `with_structured_output`，后者也作为工具 schema。Agent 的 `response_format` 解决的是“最终答复”契约，两者不要混为一谈。
