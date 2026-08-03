# 第 6 章：预制 Middleware

Middleware 在模型或工具节点前后执行，解决横切问题，不承担业务状态机。按顺序传入 `middleware=[...]`；顺序会影响谁先观察和修改请求。

```python
middleware = [
    SummarizationMiddleware(model=model, trigger=("messages", 8), keep=("messages", 4)),
    ModelCallLimitMiddleware(run_limit=4, thread_limit=12, exit_behavior="end"),
]
agent = create_agent(model, tools=tools, middleware=middleware)
```

| Middleware | 关键参数 | 适用场景 |
| --- | --- | --- |
| `SummarizationMiddleware` | `model`、`trigger`、`keep`、`summary_prompt` | 历史接近上下文预算时总结旧消息；trigger 可为 `("messages", n)`、`("tokens", n)`、`("fraction", f)` |
| `ModelCallLimitMiddleware` | `run_limit`、`thread_limit`、`exit_behavior` | 防止单次运行或一段会话无限模型调用；`end` 正常结束，`error` 让调用方处理 |

摘要是有损压缩，不是审计归档；重要事实应有独立 Store/数据库来源。调用上限也不等于费用上限，工具、输入 token 和不同模型仍可能产生不同成本。运行 [10_prebuilt_middleware.py](/knowledge-notes/examples/langchain-v1/examples/10_prebuilt_middleware.py) 以低阈值展示 call limit 的确定性边界；真实模型调用只发生在正常路径。

当前 `deep_researcher.py` 用 `max_react_tool_calls` 和 `max_researcher_iterations` 手工终止循环，功能上类似限制，但它们是该图的显式业务控制，不能误称为 LangChain middleware。
