# 第 11 章：配置、密钥、身份与运行时边界

Agent 能运行不代表它的运行边界正确。本项目把“研究内容”“运行参数”“认证身份”“长期 token”分在不同位置；把它们混在一起，是最常见也最危险的错误。

## 1. `Configuration`：一份可验证的运行参数契约

[configuration.py](https://github.com/ljxpython/open_deep_research/blob/main/src/open_deep_research/configuration.py) 的 `Configuration` 是 Pydantic `BaseModel`，描述了模型、搜索、并发和 MCP 选项：

```python
class Configuration(BaseModel):
    allow_clarification: bool = True
    max_concurrent_research_units: int = 5
    search_api: SearchAPI = SearchAPI.TAVILY
    research_model: str = DEFAULT_OPENAI_MODEL
    mcp_config: MCPConfig | None = None
```

当前节点从 `Runtime.context` 读取已经校验好的配置：

```python
async def researcher(state: ResearcherState, runtime: Runtime[Configuration]):
    settings = runtime.context
```

新调用方在构图和运行时显式声明 context：

```python
graph = StateGraph(AgentState, context_schema=Configuration).compile()
result = await graph.ainvoke(
    graph_input,
    context=Configuration.from_env(),
)
```

`Configuration.from_env()` 读取环境变量，未提供的字段继续使用 Pydantic 默认值。单次调用需要覆盖时，直接构造、校验或复制 `Configuration`，不要把业务字段塞进 `RunnableConfig`。`user_id`、`supabase_access_token` 和 `api_keys` 是请求级敏感字段，必须由受信任调用入口显式放入 context，不从进程环境自动加载。

## 2. `Runtime.context` 与 `RunnableConfig` 的边界

项目把业务配置放在 `Runtime.context`，把运行控制放在 `RunnableConfig`：

```python
async def researcher(
    state: ResearcherState,
    runtime: Runtime[Configuration],
):
    settings = runtime.context
```

`RunnableConfig` 适合装载：

- `configurable.thread_id` 等 checkpointer 运行参数。
- tags、callbacks、metadata、recursion limit 等 LangChain/LangGraph 运行时能力。

当前主实现不从 `RunnableConfig` 读取模型、搜索、MCP 或密钥字段；它们都属于 `Configuration`。

它不适合装载：

- 要让模型反复读到的研究结论，应放 graph state。
- 要写进用户可见报告的数据，应放 graph state 或受控的 Store。
- 明文密钥，除非明确启用前端/平台传密钥的受控模式。

模型只会看到你拼进消息和 prompt 的内容。`RunnableConfig` 本身不自动进入 prompt，这是安全边界，而不是“模型不知道配置”的缺陷。

## 3. API Key 的两种来源

[utils.py](https://github.com/ljxpython/open_deep_research/blob/main/src/open_deep_research/utils.py) 的 `get_api_key_for_model` 和 `get_tavily_api_key` 由环境变量 `GET_API_KEYS_FROM_CONFIG` 控制：

| `GET_API_KEYS_FROM_CONFIG` | OpenAI/Tavily 密钥来源 | 典型场景 |
| --- | --- | --- |
| 缺省或 `false` | 进程环境变量，如 `OPENAI_API_KEY` | 本地开发、受控服务端 |
| `true` | `Runtime.context.api_keys` | 受信任入口代传的短生命周期密钥 |

这个开关只决定“代码从哪里读”，不自动提供加密、审计或脱敏。不要把 `api_keys` 写入 graph state、日志、LangSmith metadata 或聊天消息。

第 [1 章](/knowledge-notes/docs/langgraph-langchain/01-real-model-agent/) 使用项目的模型配置完成真实模型调用；第 [5 章](/knowledge-notes/docs/langgraph-langchain/05-search-and-mcp/) 则验证了在 `search_api="none"` 时仍可安全装配本地工具。

## 4. 搜索提供商：工具执行位置不同

`SearchAPI` 可取：

| 值 | `get_search_tool` 返回 | 谁执行 |
| --- | --- | --- |
| `tavily` | 本地 `tavily_search` LangChain tool | 本项目进程调用 Tavily 和摘要模型 |
| `openai` | OpenAI 原生 web search tool 描述 | OpenAI 模型服务侧 |
| `anthropic` | Anthropic 原生 web search tool 描述 | Anthropic 模型服务侧 |
| `none` | 空列表 | 不搜索 |

`researcher_tools` 对普通工具调用执行 `tool.ainvoke`；对原生 web search，则通过 AI 响应 metadata 的 `tool_outputs` 或 `usage.server_tool_use` 判断是否已由提供商执行。把这两类路径当成一个本地 `@tool` 会导致重复搜索或格式错误。

## 5. MCP：配置、令牌交换、工具白名单

MCP 的配置由 `MCPConfig` 表示：

```python
class MCPConfig(BaseModel):
    url: str | None = None
    tools: list[str] | None = None
    auth_required: bool = False
```

`load_mcp_tools` 的顺序是：

```text
读取 mcp_config
  -> 如需认证，获取/刷新 access token
  -> 连接 <url>/mcp（streamable_http）
  -> 拉取远端 tools
  -> 去除与本地工具重名的项
  -> 仅保留配置 tools 白名单
  -> 包装认证异常
```

`auth_required=True` 时，项目以 `runtime.context.supabase_access_token` 换取 MCP token；token 存在 LangGraph Store 的 `(runtime.context.user_id, "tokens")` 命名空间中，并根据 `expires_in` 过期删除。远端工具名必须进入 `mcp_config.tools`，不能因为服务器“提供了”就全部暴露给模型。

> 当前锁定 `mcp>=1.9.4,<2`。原因是 `langchain-mcp-adapters==0.3.1` 仍依赖 MCP 1.x API；在适配器支持 MCP 2 前，不应单独升级 MCP 主版本。

## 6. 平台认证：`thread_id` 不等于 `owner`

[auth.py](https://github.com/ljxpython/open_deep_research/blob/main/src/security/auth.py) 对 LangGraph SDK 配置认证中间件：

1. `get_current_user` 验证 `Authorization: Bearer <JWT>`，通过 Supabase 取回用户。
2. 创建 thread 或 assistant 时，把 `owner = user.identity` 写入 metadata。
3. 读取、更新、删除、搜索 thread/assistant 时返回 `{"owner": user.identity}` 过滤条件。
4. Store 操作断言 namespace 第一个元素等于当前用户 identity。

`thread_id` 是一次会话/检查点的定位键；`owner` 是访问控制边界。若只相信客户端传的 `thread_id`，用户可以猜测或枚举其他人的会话。若只有 `owner` 没有 `thread_id`，又无法恢复指定会话。两者都需要。

## 7. 运行配置的最小检查

不需要模型调用就能验证 context 的配置边界；强行调用模型不会增加这部分的可信度：

```bash
uv run python -c '
from open_deep_research.configuration import Configuration
settings = Configuration(search_api="none", allow_clarification=False)
assert settings.search_api.value == "none"
assert settings.allow_clarification is False
print(settings.model_dump(exclude={"mcp_config"}))
'
```

接着运行第 [5 章](/knowledge-notes/docs/langgraph-langchain/05-search-and-mcp/) 的真实 Agent 示例，确认 `search_api="none"` 下模型工具协议仍然成立；真实 Tavily 搜索和真实 MCP 连接属于外部调用，应按密钥、费用和服务权限单独验证。

## 8. 检查清单

- 配置覆盖没有意外被 shell 环境变量抢走。
- 密钥未进入 state、prompt、打印输出或 trace metadata。
- MCP 使用显式 URL 和工具白名单。
- 认证层为 thread、assistant、store 都做了 owner 限制。
- 流式输出前确认不会把内部 state 或 token 泄露给前端。
