# 第 5 章：搜索与 MCP

## 学习目标

理解当前项目如何把搜索工具和 MCP 远端工具组装进 researcher 的工具列表，以及为什么工具存在不等于一定会被调用。

## 它是什么

搜索工具给 Agent 连接外部信息源，适合当前事件、网页内容和需要来源的研究任务。MCP 是把外部服务以标准工具协议暴露给模型的方式，当前项目通过 `MultiServerMCPClient` 从配置的 MCP server 拉取工具。`get_all_tools(config)` 是本项目的工具入口，它把内置研究工具、搜索工具和 MCP 工具合并成最终给 `bind_tools` 的列表。

## 当前项目怎么用

`src/open_deep_research/utils.py` 中的工具装配顺序：

1. 固定加入 `ResearchComplete` 和 `think_tool`。
2. 根据 `Configuration.search_api` 加搜索工具：
   - `tavily`：加入本地 `tavily_search` 工具。
   - `openai`：加入 OpenAI 原生 `web_search_preview` 工具描述。
   - `anthropic`：加入 Anthropic 原生 `web_search_20250305` 工具描述。
   - `none`：不加搜索工具。
3. 调用 `load_mcp_tools(config, existing_tool_names)` 加 MCP 工具。
4. 跳过与已有工具重名的 MCP 工具。

`researcher()` 再做：

```python
tools = await get_all_tools(config)
research_model = configurable_model.bind_tools(tools)
response = await research_model.ainvoke(messages)
```

因此，搜索/MCP 的入口不是散落在节点里，而是集中在 `get_all_tools`。

## 搜索工具的三种形态

| 配置 | 工具形态 | 谁执行 |
| --- | --- | --- |
| `SearchAPI.TAVILY` | LangChain `@tool` 函数 `tavily_search` | 本地 Python 调 Tavily API，再用模型摘要网页 |
| `SearchAPI.OPENAI` | `{"type": "web_search_preview"}` | OpenAI 模型服务侧执行 |
| `SearchAPI.ANTHROPIC` | `{"type": "web_search_20250305", ...}` | Anthropic 模型服务侧执行 |

这三种不是一回事。Tavily 是本地工具循环里的外部 API；OpenAI/Anthropic 原生搜索是模型提供商服务侧工具，项目用 `openai_websearch_called()` / `anthropic_websearch_called()` 从模型响应元数据判断是否发生过搜索。

## MCP 的边界

当前 MCP 配置在 `Configuration.mcp_config`：

```python
class MCPConfig(BaseModel):
    url: Optional[str]
    tools: Optional[List[str]]
    auth_required: Optional[bool] = False
```

`load_mcp_tools` 只有在同时满足 `url`、`tools` 和认证条件时才会连接 MCP server；连接失败会返回空列表。工具加载后还会按 `tools` 白名单过滤，避免把 MCP server 上的全部工具都暴露给模型。

本项目当前锁定 `mcp<2`，因为 `langchain-mcp-adapters==0.3.1` 仍依赖 MCP 1.x API。升级 MCP 2 要等适配器兼容后单独迁移。

## 最小真实 Agent

示例文件：[05_search_and_mcp.py](https://github.com/ljxpython/open_deep_research/blob/main/docs/langgraph-langchain-learning/examples/05_search_and_mcp.py)。

这个示例不发起真实搜索，也不连接 MCP server。它用真实模型完成一次工具选择学习：

1. 用 `get_all_tools({"configurable": {"search_api": "none"}})` 装配项目真实工具集合。
2. 只取 `think_tool` 绑定给模型。
3. 提示模型先调用 `think_tool` 做计划。
4. 本地执行 `think_tool`，生成 `ToolMessage`。
5. 再把工具结果交回模型，得到最终回答。

这样学的是“搜索/MCP 进入 Agent 的工具入口”和“工具协议”，不会额外触发 Tavily、MCP 或原生搜索。

## 运行

```bash
uv run python docs/langgraph-langchain-learning/examples/05_search_and_mcp.py
```

预期现象：

1. 输出 `可用工具`，其中包含 `ResearchComplete` 和 `think_tool`。
2. 输出 `工具调用数: 1`。
3. 输出最终回答。

## 常见误区

**以为配置了搜索工具就一定搜索。** 不一定。工具只是暴露给模型，模型是否调用取决于提示、任务和模型行为；项目还会用最大循环次数限制工具调用。

**把 Tavily、OpenAI 原生搜索、Anthropic 原生搜索当成同一层。** 不对。Tavily 是本地工具，原生搜索是模型提供商服务侧能力，检测方式和计费/元数据都不同。

**MCP server 上有什么就全给模型。** 当前项目有 `tools` 白名单和重名过滤，这是必要的安全边界。

## 本次真实验证

已使用默认 `openai:gpt-5.5` 运行一次。结果为：

```text
可用工具: ResearchComplete, think_tool
工具调用数: 1
最终答复: 学习搜索与 MCP 时最该关注的边界是：搜索只负责发现信息，MCP 负责受控地连接和调用工具，两者都不能绕过验证、权限和信任边界。
```

本次配置为 `search_api=none`，因此没有触发 Tavily、OpenAI/Anthropic 原生搜索或 MCP server 连接。
