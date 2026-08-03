# 第 7 章：自定义 `AgentMiddleware`

只在预制 middleware 无法表达需求时自定义。常用钩子：`before_agent`/`after_agent` 观察整次运行，`before_model`/`after_model` 修改或检查 state，`wrap_model_call` 动态选择模型，`wrap_tool_call` 拦截单次工具。

```python
class AllowListedTools(AgentMiddleware):
    def wrap_tool_call(self, request, handler):
        if request.tool_call["name"] not in {"multiply"}:
            return ToolMessage(
                content="该工具不在本次允许列表中。",
                name=request.tool_call["name"],
                tool_call_id=request.tool_call["id"],
                status="error",
            )
        return handler(request)
```

如果调用方使用 `ainvoke` 或 `astream`，同步钩子不足以覆盖工具路径；同时实现 `async def awrap_tool_call(self, request, handler)`，其中允许路径写 `return await handler(request)`。反过来，纯同步 `invoke` 使用 `wrap_tool_call`。这是本版 middleware 最容易遗漏的异步契约。

| 钩子 | 输入 | 适合做什么 | 不适合做什么 |
| --- | --- | --- | --- |
| `before_model(state, runtime)` | 当前 state 和 `Runtime.context` | 轻量状态校验、添加受控上下文 | 长时间 I/O |
| `after_model` | 新 `AIMessage` 已写入 state | 审查工具调用、触发 HITL | 重新实现工具循环 |
| `wrap_model_call(request, handler)` | 模型请求和继续函数 | 根据上下文选择模型、记录预算 | 悄悄改变业务输出契约 |
| `wrap_tool_call(request, handler)` | 单个 tool call | allow-list、授权、统一工具错误 | 替代工具自身的输入验证 |

Middleware 仍不是安全边界的唯一层：工具函数必须验证身份和输入，服务端必须进行授权。运行 [11_custom_middleware.py](/knowledge-notes/examples/langchain-v1/examples/11_custom_middleware.py) 会本地断言拒绝结果携带匹配的 tool call id，并真实调用允许的 `multiply`。
