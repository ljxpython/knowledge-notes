# 第 5 章：RAG 检索 Agent

## 学习目标

将 retriever 包装为工具，观察标准 Agent 怎样决定检索、接收带来源的文档片段，再生成受证据约束的回答。

## 核心机制

RAG 不要求一定使用 Agent。固定问答可直接写 `retriever | format_docs | prompt | model`；当模型需要决定“要不要检索、检索什么、是否继续用其他工具”时，把 retriever 变为 tool 更合适：

```python
@tool
def search_learning_notes(query: str) -> str:
    """Search the local learning notes."""
    return format_documents(retriever.invoke(query))


agent = create_agent(model=model, tools=[search_learning_notes])
```

工具输出必须带来源和文本片段。它会变成 `ToolMessage`，模型才能据此写答案；仅把向量分数交给模型没有可读语义。生产环境还应把 `source`、文档版本、权限过滤和引用格式作为明确 schema。

## 与当前项目的关系

项目的 `researcher()` 已通过 `get_all_tools(runtime.context, runtime.store)` 动态绑定工具。RAG tool 与 Tavily/MCP 一样可放入该列表，但应在调用前用 `Runtime.context.user_id` 过滤权限，并限制 `k`、单片段长度和总 token，防止知识库内容压垮工具上下文。

## 最小真实 Agent

[05_rag_agent.py](/knowledge-notes/examples/langchain-v1/examples/05_rag_agent.py) 建立内存 retriever，定义 `search_learning_notes`，并要求 `create_agent` 先调用它再回答：

```bash
uv run python docs/langchain/examples/05_rag_agent.py
```

它会产生 embedding 和一次或多次模型调用，未调用网页、MCP 或数据库。

### 当前验证记录

本章依赖第 4 章的真实 embedding 索引。当前 API 网关对 `text-embedding-3-small` 返回 503 `model_not_found`，所以 Agent 尚未进入工具循环。本章保持真实 retriever/embedding 实现，状态为“受外部条件阻塞”，而非以 mock 检索结果伪造 RAG 验证。

## 常见误区

- “要求必须调用工具”只是 prompt 约束；关键任务仍应通过应用侧校验 `ToolMessage` 或路由保证。
- 检索到文档不等于文档可信或最新，应保留来源并做索引更新。
- 不要把原始文档不加长度限制地返回工具；应按 chunk、`k` 和 token 预算截断。
