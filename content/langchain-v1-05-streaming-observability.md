# 第 5 章：流式输出与观测

`ainvoke` 适合只要最终 state；`astream` 适合 UI 或实时日志；`astream_events(version="v2")` 适合查看 Runnable/Agent 的嵌套生命周期。三者都执行真实工作，不要为了“流式”重复调用 Agent。

```python
async for chunk in agent.astream(input, stream_mode="updates"):
    print(chunk)  # 节点 state 更新，不等同于纯文本 token

async for event in agent.astream_events(input, version="v2", config=config):
    if event["event"] == "on_chat_model_start":
        print(event["name"])
```

| 参数/概念 | 用法 |
| --- | --- |
| `stream_mode="updates"` | 节点完成后的 state patch；最适合 Agent 调试 |
| `stream_mode="messages"` | 模型消息 token/metadata 流；最适合聊天 UI |
| `astream_events(..., version="v2")` | event 名称、run id、parent ids、tags、metadata；用于链路诊断 |
| `config["tags"]` | 非敏感分类，如 `learning`、`agent`；可在 LangSmith 筛选 |
| `config["metadata"]` | 非敏感诊断键值；可能被追踪后端保存 |

LangSmith 只在环境变量启用后接收 trace；本地 event 流不要求远端观测服务。禁止把 API key、JWT、完整用户消息、检索全文写进 tags/metadata。当前项目的 `langsmith:nostream` 是其 trace 标签约定，不是 Python 的 async 开关。

运行 [09_streaming_observability.py](/knowledge-notes/examples/langchain-v1/examples/09_streaming_observability.py) 会进行一次很短的 Agent 调用，同时打印 node update 和模型启动事件。
