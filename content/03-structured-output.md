# 第 3 章：结构化输出

## 学习目标

理解为什么当前项目不用模型随便回一段自然语言，而是让模型按 `BaseModel` 定义的字段返回对象。

## 它是什么

`BaseModel` 定义运行时可校验的数据契约，`Field` 给字段补默认值、说明和约束。`with_structured_output(MyModel)` 会让聊天模型按这个 schema 返回 `MyModel` 实例。它解决的问题是：后续代码可以读 `response.research_brief`、`response.need_clarification` 这种明确字段，而不是从一段文本里猜。

## 当前项目怎么用

| 模型 | 当前项目位置 | 用途 |
| --- | --- | --- |
| `ClarifyWithUser` | `state.py` | 让模型判断是否需要追问用户。 |
| `ResearchQuestion` | `state.py` | 把用户消息转成研究 brief。 |
| `ConductResearch` | `state.py` | 作为 supervisor 可调用的结构化工具 schema。 |
| `Summary` | `state.py` | 约束网页摘要结果。 |
| `ResearcherOutputState` | `state.py` | 限制 researcher 子图输出给父图的字段。 |

项目里的典型写法：

```python
research_model = (
    configurable_model
    .with_structured_output(ResearchQuestion)
    .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
    .with_config({
        "configurable": research_model_config,
        "tags": ["langsmith:nostream"],
    })
)
response = await research_model.ainvoke(
    [HumanMessage(content=prompt_content)],
    config=config,
)
```

注意这个顺序：先把模型包装成结构化输出，再加重试和运行时配置。返回值已经是 Pydantic 对象，不是 `AIMessage`。

## 最小真实 Agent

示例文件：[03_structured_output.py](/knowledge-notes/examples/langgraph-langchain/examples/03_structured_output.py)。

```python
class TopicBrief(BaseModel):
    title: str = Field(description="A short Chinese title.")
    research_question: str = Field(description="One focused research question.")
    needs_tools: bool = Field(description="Whether external tools are needed.")
```

节点调用真实模型：

```python
structured_model = model.with_structured_output(TopicBrief)
brief = await structured_model.ainvoke([...])
```

然后把 `brief.model_dump_json()` 写回 `messages`，方便你直接看到 schema 约束后的结果。

## `BaseModel`、`Field` 什么时候用

| 场景 | 选择 |
| --- | --- |
| 模型必须返回可被代码继续处理的字段 | `BaseModel + Field` |
| 工具参数需要让模型理解字段含义 | `BaseModel + Field` |
| 图内部状态只做读写和 reducer 合并 | `TypedDict` |
| 对话历史 | `MessagesState` |

Field 的 `description` 很重要，尤其给模型看的工具参数和结构化输出字段。别为了好看给所有普通状态字段都套 `Field`，那是噪音。

## 运行

```bash
uv run python docs/langgraph-learning/examples/03_structured_output.py
```

预期现象：终端输出一段 JSON，至少包含 `title`、`research_question`、`needs_tools` 三个字段。它不是 mock，是模型按 Pydantic schema 生成并通过解析后的对象。

## 常见误区

**把结构化输出当成 100% 业务正确。** Pydantic 只保证形状和类型，不能保证模型判断一定对；当前项目因此加了 `.with_retry(...)`，但业务质量仍要靠提示词、评估和后续节点约束。

**以为结构化输出返回 `AIMessage`。** `with_structured_output(TopicBrief)` 返回的是 `TopicBrief` 实例；如果要放进 `messages`，需要自己转成字符串或重新包装成 `AIMessage`。

**把工具 schema 和图状态混在一起。** `ConductResearch` 是工具/模型边界契约；`ResearcherState` 是图内部状态。一个强调校验和字段说明，一个强调状态合并。

## 本次真实验证

已使用默认 `openai:gpt-5.5` 运行一次。模型返回：

```json
{"title":"LangGraph 状态管理机制研究","research_question":"LangGraph 如何通过状态模式（State Schema）、节点状态更新与检查点机制实现多轮工作流中的状态管理与恢复？","needs_tools":false}
```
