# 第 3 章：标准 Agent 与 Middleware

## 学习目标

理解 LangChain v1 的 `create_agent` 是什么、它怎样处理工具循环、何时应使用它，以及 middleware 应放在哪一层。

## 核心机制

`create_agent(model, tools, ...)` 返回一个 `CompiledStateGraph`。运行时模型生成 `AIMessage.tool_calls`，框架执行工具、回填 `ToolMessage`、再调用模型，直到没有工具调用。它适合一个模型加一组工具的标准 ReAct 循环。

```python
agent = create_agent(
    model=model,
    tools=[multiply],
    system_prompt="计算时必须调用 multiply。",
    response_format=CalculationAnswer,
)
result = await agent.ainvoke({"messages": [{"role": "user", "content": "23 * 7"}]})
```

`response_format=BaseModel` 要求最终答复按 schema 返回，结果位于 `result["structured_response"]`。middleware 是在模型调用、工具调用等生命周期钩子处加入横切逻辑的扩展点，适合鉴权、动态模型选择、限额、审计或统一错误策略。不要用 middleware 承载业务状态机。

## 与当前项目的关系

当前项目手写 `researcher -> researcher_tools -> researcher`，因为它需要 supervisor、多 researcher 子图、压缩和自定义 state。单一 researcher 的简单版本可以替换为 `create_agent`；整条深度研究流程不应强行压成一个标准 Agent。

## 最小真实调用

运行 [03_create_agent.py](/knowledge-notes/examples/langchain-v1/examples/03_create_agent.py)：模型必须调用本地 `multiply`，再返回 `CalculationAnswer`。

```bash
uv run python docs/langchain/examples/03_create_agent.py
```

## 常见误区

- `create_agent` 不是“没有 LangGraph”：它返回已编译图，只是框架替你维护标准循环。
- `response_format` 不验证工具执行的事实正确性，只验证最终结构。
- tool docstring 是模型选择工具的重要语义，不是可随意省略的注释。

官方参考：[create_agent](https://reference.langchain.com/python/langchain/agents/factory/create_agent)。
