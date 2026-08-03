# 第 1 章：Prompt 与消息模板

## 学习目标

用 `ChatPromptTemplate` 把稳定指令、对话历史和本次问题组合为消息列表，而不是在每个节点手写 f-string。

## 核心机制

`ChatPromptTemplate` 是一个 Runnable：输入变量字典，输出可交给 chat model 的 `ChatPromptValue`。`from_messages` 接受角色和模板；`MessagesPlaceholder` 专门插入已有 `HumanMessage`、`AIMessage`、`ToolMessage` 列表；`partial` 预填不会随调用变化的变量。

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "你面向 {audience} 回答。"),
    MessagesPlaceholder("history", optional=True),
    ("human", "{question}"),
]).partial(audience="Python 初学者")
```

数据流是 `dict -> ChatPromptValue(messages) -> AIMessage`。变量缺失会在格式化阶段报错；placeholder 的 `optional=True` 只适用于确实允许没有历史的场景。

## 与当前项目的关系

`src/open_deep_research/prompts.py` 目前存放普通字符串模板，节点用 `.format(...)` 后再创建 `HumanMessage`/`SystemMessage`。这是可行的，但当模板要混入多轮消息、工具消息或复用 partial 变量时，`ChatPromptTemplate` 更不易漏角色或漏变量。不要把 `Runtime.context.api_keys`、token、完整用户档案放入模板变量。

## 最小真实调用

运行 [01_prompt_templates.py](/knowledge-notes/examples/langchain-v1/examples/01_prompt_templates.py)：

```bash
uv run python docs/langchain/examples/01_prompt_templates.py
```

它调用一次模型，验证 `history` 被保留为消息、`audience/style` 被 partial 预填，并通过 `StrOutputParser` 将最终 `AIMessage.content` 转成字符串。

## 常见误区

- 把 `MessagesPlaceholder` 当字符串插槽：它应接收消息序列，不能直接接未序列化的工具结果 dict。
- 把所有用户资料拼进 system prompt：只传模型回答需要的脱敏字段；身份和凭据仍在 `Runtime.context`。
- 把模板当安全边界：模板只格式化数据，不能自动防 prompt injection 或数据泄露。

官方参考：[ChatPromptTemplate](https://reference.langchain.com/python/langchain-core/prompts/chat/ChatPromptTemplate)。
