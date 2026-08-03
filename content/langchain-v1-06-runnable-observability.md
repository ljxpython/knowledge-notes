# 第 6 章：Runnable 观测与生产边界

## 学习目标

区分模型配置、运行追踪配置和业务 context，学会在 LCEL 链上使用 tags、metadata 与 `astream_events`。

## 核心机制

`with_config` 返回带默认运行配置的新 Runnable：

```python
chain = (prompt | model | StrOutputParser()).with_config({
    "tags": ["learning", "rag"],
    "metadata": {"lesson": "06"},
})
```

tags 和 metadata 会沿子 Runnable 传播，适合 LangSmith 过滤、运行归类和调试。不要放 API Key、JWT、完整用户信息或文档正文。`astream_events(..., version="v2")` 返回 prompt、model、parser 等子步骤的事件，可观察链的层级与耗时。

| 数据 | 位置 |
| --- | --- |
| 模型名称、max tokens | 模型构造参数或 `with_config({"configurable": ...})` |
| tags、metadata、callbacks | Runnable config 顶层 |
| 用户身份、密钥、权限 | `Runtime.context` 或受控服务端 |
| 消息、检索结果、回答 | graph state 或 Runnable 输入输出 |

当前项目的 `langsmith:nostream` 是标签约定，不是 Python async 开关。主图的 `astream_events` 在第 7 章讲的是图事件；本章讲的是 prompt/model/parser 组成的 Runnable 链事件。

## 最小真实验证

运行 [06_runnable_observability.py](/knowledge-notes/examples/langchain-v1/examples/06_runnable_observability.py)：

```bash
uv run python docs/langchain/examples/06_runnable_observability.py
```

它执行一次链并输出启动事件顺序。启用 LangSmith 环境变量时，同一运行可在 trace 中按 tag 查找。

## 常见误区

- metadata 不是安全存储，也可能被追踪后端持久化。
- 事件流不等于最终文本流：事件包含生命周期和嵌套 Runnable，UI 文本输出通常用 `astream`。
- `max_concurrency` 控制 Runnable batch 并发，不等于项目的 `max_concurrent_research_units` 业务上限。
