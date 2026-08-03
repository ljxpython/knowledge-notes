# 第 4 章：文档、切分、Embedding 与 Retriever

## 学习目标

建立最小本地 RAG 索引，并理解 RAG 的每层输出是什么，而不是把“向量数据库”当黑盒。

## 索引与检索链

```text
原始内容
  -> Document(page_content, metadata)
  -> RecursiveCharacterTextSplitter
  -> chunks
  -> Embeddings.embed_documents
  -> InMemoryVectorStore
  -> retriever.invoke(query)
  -> list[Document]
```

`Document.page_content` 是给 embedding 和模型的文本；`metadata` 保存来源、权限标签、时间等可过滤或可展示的信息。splitter 解决上下文窗口和检索粒度问题。embedding 把文本变为向量，vector store 保存并相似度搜索，retriever 则把任何存储实现统一成“查询字符串 -> 文档列表”的 Runnable 接口。

```python
chunks = RecursiveCharacterTextSplitter(
    chunk_size=100, chunk_overlap=20
).split_documents(documents)
store = InMemoryVectorStore.from_documents(
    chunks,
    init_embeddings("openai:text-embedding-3-small"),
)
retriever = store.as_retriever(search_kwargs={"k": 2})
```

## 参数取舍

| 参数 | 太小 | 太大 |
| --- | --- | --- |
| `chunk_size` | 上下文断裂、召回片段缺信息 | 噪声多、浪费 token、召回不精确 |
| `chunk_overlap` | 跨边界语义丢失 | 索引重复、embedding 成本上升 |
| `k` | 漏证据 | prompt 膨胀、无关内容干扰 |

当前项目没有本地文档 RAG：它通过 Tavily、原生 Web Search 和 MCP 获取外部信息。需要私有知识库时，可在 `get_all_tools` 增加受权限控制的 retriever tool；不要直接把所有文档塞进 `researcher_messages`。

## 最小真实验证

[04_documents_and_retrieval.py](/knowledge-notes/examples/langchain-v1/examples/04_documents_and_retrieval.py) 用固定三段本地学习资料创建 `Document`，调用真实 OpenAI embedding，再在内存中召回两段文本：

```bash
uv run python docs/langchain/examples/04_documents_and_retrieval.py
```

它不联网抓网页、不写持久化数据库，但 embedding API 会产生少量费用。

### 当前验证记录

构图和编译已通过。真实 embedding 调用在当前 API 网关返回 503 `model_not_found`：该网关没有 `text-embedding-3-small` 可用渠道。因此本章状态为“受外部条件阻塞”；示例没有降级为 fake embedding，待可用 embedding 渠道恢复后重跑即可完成真实检索验证。

## 常见误区

- embedding 不等于生成模型：它输出向量，不能直接回答用户。
- `InMemoryVectorStore` 进程结束即丢失，生产知识库需持久化 store、索引版本和删除策略。
- metadata 不能代替权限：检索前后都应按用户身份过滤可见文档。

官方参考：[组件架构](https://docs.langchain.com/oss/python/langchain/component-architecture)。
