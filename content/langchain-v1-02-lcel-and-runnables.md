# 第 2 章：LCEL 与 Runnable

## 学习目标

理解 LangChain Expression Language（LCEL）如何把可调用组件串联、并行和改写数据，并知道它何时比 `StateGraph` 更合适。

## 核心机制

所有 Runnable 都有统一的 `invoke/ainvoke`、`batch/abatch`、`stream/astream` 接口。`a | b` 表示前者输出作为后者输入：

```python
chain = prepare | prompt | model | StrOutputParser()
```

| Runnable | 输入到输出 | 常用场景 |
| --- | --- | --- |
| `RunnableLambda` | 任意 Python 函数 | 纯数据清洗、格式转换 |
| `RunnableParallel` | 同一输入到多个分支，输出 dict | 独立并行计算或准备多个 prompt 字段 |
| `RunnablePassthrough.assign` | 保留 dict 并增加键 | 给下游增加 derived field，不丢原输入 |
| `ChatPromptTemplate` | dict 到消息 | 将结构化输入转为模型输入 |

LCEL 不保存状态、不做分支路由，也不提供 checkpoint；它适合固定的数据管道。需要循环、动态跳转、子图或持久化时，用当前项目的 `StateGraph`。

## 与当前项目的关系

`deep_researcher.py` 目前直接调用模型，是因为每个节点的状态更新和 `Command` 跳转都需要显式控制。可把单个节点内部稳定的“准备 prompt -> 调模型 -> 解析”重构为 LCEL，但不要用 LCEL 取代 supervisor/researcher 图。

## 最小真实调用

[02_lcel_runnables.py](/knowledge-notes/examples/langchain-v1/examples/02_lcel_runnables.py) 先本地运行 `RunnableParallel`，再用 `RunnableLambda -> assign -> prompt -> model -> parser` 发起一次模型调用：

```bash
uv run python docs/langchain/examples/02_lcel_runnables.py
```

## 常见误区

- `|` 不是 shell 管道：前后组件的 Python 输入输出类型必须匹配。
- `assign` 不是原地修改：它返回新的输出 dict，原输入不会被可变修改。
- 对有副作用的函数盲目 `batch`：并发会放大费用、限流和写入风险。

官方参考：[RunnablePassthrough](https://reference.langchain.com/python/langchain-core/runnables/passthrough/RunnablePassthrough)。
