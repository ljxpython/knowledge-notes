# 第 1 章：真实模型与消息

## 学习目标

跑通一个最小 Agent 闭环：`HumanMessage` 进入 `MessagesState`，图节点通过真实模型的 `ainvoke` 得到 `AIMessage`，再把它更新回图状态。

## 它是什么

LangChain 的消息对象把“谁说的话、说了什么、是否带工具调用”等对话语义统一起来，避免直接拼字符串。`init_chat_model` 创建可配置聊天模型；本项目在 `deep_researcher.py` 中用同一模式，让研究、压缩和报告节点按运行时配置选择模型。`ainvoke` 是异步的一次真实模型调用。

当前项目证据：

- `deep_researcher.py` 的 `configurable_model = init_chat_model(...)` 声明了可配置模型。
- `researcher()` 用 `research_model.ainvoke(messages)` 调用模型。
- `researcher()` 返回 `{"researcher_messages": [response]}`，把模型返回的 `AIMessage` 交给状态 reducer 合并。

## 最小真实 Agent

示例文件：[01_real_model_agent.py](https://github.com/ljxpython/open_deep_research/blob/main/docs/langgraph-langchain-learning/examples/01_real_model_agent.py)。

```python
graph = (
    StateGraph(MessagesState)
    .add_node("answer", answer)
    .add_edge(START, "answer")
    .add_edge("answer", END)
    .compile()
)
```

`MessagesState` 自带 `messages` 状态字段及消息 reducer。因此节点返回一个新消息：

```python
return {"messages": [response]}
```

最终状态仍保留最初的 `HumanMessage`，并追加模型产生的 `AIMessage`。这就是后续多轮 Agent、工具调用和子图上下文的基础。

## 运行

```bash
uv run python docs/langgraph-langchain-learning/examples/01_real_model_agent.py
```

预期现象：终端输出一行模型回复，内容是对“LangGraph 的作用”的简短说明。调用只使用本地模型配置，不调用搜索、MCP、数据库或项目的完整深度研究图。

脚本会用 `python-dotenv` 读取仓库根目录的 `.env`，因此无需把密钥手工 export 到当前 shell；密钥不会被打印。

## 本次真实验证

已使用默认 `openai:gpt-5.5` 运行一次。模型返回：

```text
LangGraph 用于构建、编排和运行带有状态与循环控制的多步骤 AI Agent 工作流。
```

## 常见误区

**把 `ainvoke` 当成 Agent。** `ainvoke` 只是一次模型调用；本例之所以是最小 Agent，是因为模型调用被放进了可执行的 `StateGraph` 节点，并且读写了图状态。真正的工具型 Agent 会在后续章节加入 `bind_tools`、`ToolMessage` 和循环路由。

**直接传字符串就够了。** 很多模型接口接受字符串，但项目实际使用消息对象。工具调用时必须保留 `AIMessage.tool_calls` 和匹配的 `ToolMessage.tool_call_id`，字符串会丢掉这些协议语义。

**配置只能从环境变量读。** 本项目的 `Configuration.from_runnable_config` 会优先读取环境变量，也支持从 `RunnableConfig["configurable"]` 读取；示例沿用该机制。
