# 第 14 章：旧版与当前版 API 对照

## 学习目标

本章专门解决一个实际问题：项目为什么需要改代码，哪些改动只是参数改名，哪些改动会改变运行时语义。读完后，看到旧教程中的 `config_schema`、`input`、顶层模型配置时，不会机械照抄，也不会把所有旧代码都误判成必须重写。

本章依据当前锁文件和当前官方 Python API。项目的 `src/legacy` 不作为迁移目标；对照对象是 `src/open_deep_research` 和 `docs/langgraph-learning/examples`。

## 1. 迁移总表

| 主题 | 旧写法 | 当前推荐写法 | 为什么改 | 本项目处理 |
| --- | --- | --- | --- | --- |
| 输入 schema | `StateGraph(State, input=Input)` | `StateGraph(State, input_schema=Input)` | 参数名表达更清楚，并与 `output_schema` 对称 | 主图已替换 |
| 输出 schema | `StateGraph(State, output=Output)` | `StateGraph(State, output_schema=Output)` | 旧别名已进入弃用路径 | researcher 子图已替换 |
| 图配置 schema | `config_schema=Configuration` | `context_schema=Configuration` | `config_schema` 在 LangGraph v1 已弃用，未来会移除 | 主图和示例已迁移，不保留旧业务配置入口 |
| 运行时业务上下文 | 从 `config["configurable"]` 手工读取 | `context_schema` + `Runtime[Context]` + `invoke(..., context=...)` | 类型、职责和数据流更明确 | 主图和 01–09 示例已使用 |
| LangChain 动态模型参数 | `with_config({"model": ..., "max_tokens": ...})` | `with_config({"configurable": {"model": ..., "max_tokens": ...}, "tags": [...]})` | `configurable_fields` 属于 `RunnableConfig["configurable"]` 命名空间 | 主实现和 01–08 示例已替换 |
| 运行观测配置 | 和模型字段混在同一个字典 | `tags`、`metadata`、`callbacks` 放在 config 顶层 | 这些字段属于 LangChain 运行控制，不是模型业务参数 | 已在模型配置示例中分层 |
| 模型初始化 | `langchain_classic` 的 `init_chat_model` | `from langchain.chat_models import init_chat_model` | LangChain v1 的主包持续维护新 API | 项目已使用当前导入 |
| 普通 Agent | 手写完整工具循环 | `create_agent` 可作为默认方案 | 标准循环由框架维护，减少边缘错误 | 本项目保留手写图，因为它需要 supervisor、子图和自定义状态 |

## 2. `StateGraph` 参数为什么改名

当前 `StateGraph` 的 Python 签名是：

```python
StateGraph(
    state_schema,
    context_schema=None,
    *,
    input_schema=None,
    output_schema=None,
)
```

旧教程常见的写法如下：

```python
StateGraph(
    AgentState,
    input=AgentInputState,
    output=ResearcherOutputState,
    config_schema=Configuration,
)
```

这里其实混合了三类东西：

1. `AgentState` 是图内部节点通信使用的完整 state。
2. `input`/`output` 是图的外部输入输出过滤器。
3. `config_schema` 是旧的运行配置 schema。

当前写法把三类职责明确分开：

```python
StateGraph(
    AgentState,
    context_schema=Configuration,
    input_schema=AgentInputState,
    output_schema=ResearcherOutputState,
)
```

`input_schema` 和 `output_schema` 不会改变内部 state 的 reducer，也不会把内部节点都限制成只能读写输入字段。它们主要约束图的外部入口和 `invoke` 返回值。内部 state 仍然是所有节点通信所需字段的联合。

## 3. `config_schema` 为什么不能机械替换

`config_schema` 的弃用不等于“把字符串替换成 `context_schema`”就结束了。两者的职责不同：

| 维度 | `RunnableConfig` | `Runtime.context` |
| --- | --- | --- |
| 典型内容 | callbacks、tags、metadata、recursion_limit、thread_id、模型可配置字段 | user_id、模型依赖、数据库连接、feature flag 等本次运行上下文 |
| 传入方式 | `graph.invoke(input, config=...)` | `graph.invoke(input, context=...)` |
| 节点读取 | `config: RunnableConfig` | `runtime: Runtime[Context]` |
| 是否属于 graph state | 否 | 否 |
| 是否适合长期持久化 | 通常不适合 | 通常不适合；持久数据使用 Store |
| 当前状态 | 仍然有效 | 当前推荐的显式上下文 API |

当前官方示例：

```python
from dataclasses import dataclass
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime


@dataclass
class Context:
    model_provider: str = "openai"


def node(state: State, runtime: Runtime[Context]):
    provider = runtime.context.model_provider
    return {"answer": f"use {provider}"}


graph = (
    StateGraph(State, context_schema=Context)
    .add_node("node", node)
    .add_edge(START, "node")
    .add_edge("node", END)
    .compile()
)

graph.invoke({}, context=Context(model_provider="openai"))
```

本项目把 `Configuration` 作为 `context_schema`，节点只从 `Runtime.context` 读取业务配置。`Configuration.from_runnable_config()` 已从当前实现删除；旧平台必须在调用边界完成迁移并传入 `context=Configuration(...)`。

新代码的参考实现见：[09_runtime_context.py](/knowledge-notes/examples/langgraph-langchain/examples/09_runtime_context.py)。它使用：

```python
StateGraph(MessagesState, context_schema=Configuration)
```

以及：

```python
async def answer(
    state: MessagesState,
    runtime: Runtime[Configuration],
):
    settings = runtime.context
```

当前主实现的节点不声明 `RunnableConfig`。调用图时仍可传 `config={"tags": [...], "configurable": {"thread_id": ...}}` 控制追踪和 checkpoint；只有新节点确实要读取这些运行控制信息时，才额外声明 `config: RunnableConfig`。业务配置仍只从 `runtime.context` 读取。

新代码的标准调用方式：

```python
settings = Configuration(
    research_model="openai:gpt-5.5",
    max_react_tool_calls=6,
)
result = await graph.ainvoke(
    {"messages": messages},
    context=settings,
    config={"tags": ["research"]},
)
```

### `context_schema` 到底做了什么

可以把它理解成一条**运行时上下文通道的类型声明**：

```text
调用方 context=...
       |
       v
StateGraph(context_schema=Context)
       |
       v
节点 runtime: Runtime[Context]
       |
       v
runtime.context
```

它解决的是“节点怎样获得本次运行的业务依赖”，不是“怎样保存工作流状态”。完整实现固定分五步：

1. 定义 context 类型，描述模型、用户、租户、feature flag 或其他本次运行依赖。
2. 构图时传入 `context_schema=Context`。
3. 节点签名声明 `runtime: Runtime[Context]`。
4. 调用图时使用关键字参数 `context=...`。
5. 节点从 `runtime.context` 读取字段，不把它复制回 state。

## 3.1 最小实现：从定义到调用

下面代码是不依赖项目业务的完整最小版本：

```python
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel


class AgentState(TypedDict):
    question: str
    answer: str


class Context(BaseModel):
    model_name: str = "openai:gpt-5.5"
    user_id: str | None = None
    concise: bool = True


def answer(state: AgentState, runtime: Runtime[Context]):
    context = runtime.context
    suffix = "（简洁回答）" if context.concise else ""
    return {"answer": f"{context.user_id}: {state['question']} {suffix}"}


graph = (
    StateGraph(AgentState, context_schema=Context)
    .add_node("answer", answer)
    .add_edge(START, "answer")
    .add_edge("answer", END)
    .compile()
)

result = graph.invoke(
    {"question": "LangGraph 做什么？", "answer": ""},
    context=Context(user_id="u-001", concise=True),
)
```

调用后数据的职责仍然分开：

| 数据 | 位置 | 例子 | 是否由 reducer 合并 |
| --- | --- | --- | --- |
| 工作流业务数据 | `state` | `question`、`answer`、消息、工具结果 | 是，按 state schema 决定 |
| 本次运行依赖 | `runtime.context` | `model_name`、`user_id`、feature flag | 否 |
| 运行控制 | `config` | `tags`、callbacks、`thread_id`、`recursion_limit` | 否 |

### `context_schema` 支持什么类型

当前 LangGraph 接受常见的 `TypedDict`、`dataclass` 和 Pydantic `BaseModel` 作为 schema。选择方式如下：

| 类型 | 读取方式 | 适合场景 | 本项目选择 |
| --- | --- | --- | --- |
| Pydantic `BaseModel` | `runtime.context.research_model` | 需要默认值、枚举、类型转换和配置校验 | `Configuration` |
| `dataclass` | `runtime.context.model_provider` | 轻量、明确、主要依赖类型检查 | 官方简单示例 |
| `TypedDict` | `runtime.context["user_id"]` | 已经使用字典契约、希望最少运行时逻辑 | 可用于简单实验 |

本项目选择 Pydantic 不是 LangGraph 强制要求，而是因为 `Configuration` 已经包含 `SearchAPI`、默认值、数值限制和 MCP 嵌套配置。`Configuration.from_env()` 负责从环境变量构造它，LangGraph 只负责把这个对象放入 `Runtime.context`。

### 必须传 context 实例，不要指望 LangGraph 自动转换字典

推荐写法：

```python
context = Configuration.from_env()
result = await graph.ainvoke(input_value, context=context)
```

或在单次运行中显式构造：

```python
context = Configuration(
    research_model="openai:gpt-5.5",
    search_api="none",
    max_react_tool_calls=4,
)
```

在当前锁定版本中，`context_schema=Configuration` 主要提供上下文类型契约；如果调用方传入普通字典，LangGraph 可能原样放进 `runtime.context`，不会自动执行 `Configuration(**context)`。此时下面的属性访问会失败：

```python
# 不推荐：runtime.context 可能只是 dict，没有 .research_model 属性。
await graph.ainvoke(input_value, context={"research_model": "openai:gpt-5.5"})
```

所以转换责任应放在调用入口：`Configuration.from_env()`、`Configuration(...)` 或明确的 `Configuration.model_validate(raw_context)`。这也保证 Pydantic 的枚举和数值校验真的发生。

### `context` 必须用关键字传递

`invoke`/`ainvoke` 的第二个位置参数是旧的 `config` 入口，不是 context：

```python
await graph.ainvoke(
    input_value,
    context=Configuration.from_env(),
    config={"tags": ["learning"]},
)
```

不要写成：

```python
# 这会把字典当作 RunnableConfig，而不是 Runtime.context。
await graph.ainvoke(input_value, {"research_model": "openai:gpt-5.5"})
```

### 子图不会自动获得父图的 context

父节点调用已编译子图时，应显式转交相同 context：

```python
async def run_researchers(
    state: ParentState,
    runtime: Runtime[Configuration],
):
    result = await researcher_graph.ainvoke(
        {"topic": state["topic"]},
        context=runtime.context,
    )
    return {"summary": result["summary"]}
```

子图也要声明自己的 `context_schema=Configuration`。本项目的主图、supervisor 子图和 researcher 子图都这样做；`deep_researcher.py` 在调用子图时显式传递 context，不能假设子图会从父节点的 `Runtime` 对象中自动读取。

### 当前项目的真实实现路径

项目的配置流是：

```text
Configuration.from_env()
  -> deep_researcher.ainvoke(..., context=configuration)
  -> StateGraph(..., context_schema=Configuration)
  -> node(..., runtime=Runtime[Configuration])
  -> runtime.context
  -> configurable.research_model / search_api / limits
```

`get_all_tools(context, store)`、API key 和 MCP 辅助函数也直接接收 `Configuration`；不存在把 context 投影回 `config["configurable"]` 的兼容层。

### 最常见的五个错误

1. **只改构图参数，不改节点签名**：把 `config_schema` 改成 `context_schema`，节点却仍只声明 `config: RunnableConfig`，新 context 不会出现在 `config` 里。
2. **把 context 当 state**：模型选择、用户 ID、租户依赖不应写入消息 state，否则会被 reducer、checkpoint 或 prompt 意外传播。
3. **把 tags 放进 context**：`tags`、callbacks、metadata 是运行观测控制，应放 `config` 顶层。
4. **把 context 当持久化 Store**：需要跨线程长期保存的数据使用 checkpointer/Store；context 只属于当前运行。
5. **子图漏传 context**：子图节点读取到 `None` 或默认值，造成父子图使用不同模型、搜索配置或限额。

### 本章的本地验证

无模型调用的最小验证：

```bash
uv run python -c '
from open_deep_research.configuration import Configuration
settings = Configuration(search_api="none", max_react_tool_calls=4)
assert settings.search_api.value == "none"
assert settings.max_react_tool_calls == 4
print("context schema input ok")
'
```

真实模型验证：

```bash
uv run python docs/langgraph-learning/examples/09_runtime_context.py
```

该示例真实调用当前配置的模型，节点从 `runtime.context` 读取 `research_model` 和 `research_model_max_tokens`，并通过 `MessagesState` 返回模型消息。

## 4. `with_config` 的新旧差别

项目已经声明：

```python
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)
```

这表示这三个字段可通过 `RunnableConfig["configurable"]` 在运行时覆盖。

旧写法：

```python
model = configurable_model.with_config(
    {
        "model": "openai:gpt-5.5",
        "max_tokens": 80,
        "api_key": api_key,
        "tags": ["learning"],
    }
)
```

当前写法：

```python
model = configurable_model.with_config(
    {
        "configurable": {
            "model": "openai:gpt-5.5",
            "max_tokens": 80,
            "api_key": api_key,
        },
        "tags": ["learning"],
    }
)
```

要点有三个：

1. `model`、`max_tokens`、`api_key` 是模型的可配置字段，因此放进 `configurable`。
2. `tags`、`metadata`、`callbacks` 是 Runnable 运行配置，因此放在顶层。
3. `with_config` 返回新的 Runnable，不改变全局 `configurable_model`；并发 researcher 可以各自使用不同派生配置。

模型节点直接调用：

```python
response = await model.ainvoke(messages)
```

图运行时会处理当前调用链的观测上下文；项目的模型字段由 `with_config` 绑定，业务配置不会从 `RunnableConfig` 覆盖它们。

## 5. 为什么不把项目直接改成 `create_agent`

LangChain v1 推荐用 `create_agent` 快速创建标准工具 Agent。它适合：

- 一个模型；
- 一组工具；
- 标准模型-工具-模型循环；
- 不需要自定义 supervisor 和多层子图。

当前项目不是这个形状。它有 clarification、research brief、supervisor、多个 researcher 子图、并发汇总、压缩和 final report 等显式阶段。把它整个替换成 `create_agent` 会丢失教学价值和业务状态边界，因此这里保留 `StateGraph + Command`。

这不是拒绝新 API，而是按问题选择抽象层：标准 Agent 用 `create_agent`，定制工作流继续用 `StateGraph`。

## 6. 本项目的当前边界

### 已替换

- `src/open_deep_research/deep_researcher.py` 中三张图的弃用构图参数和业务 context 入口。
- 主实现中所有动态模型 `with_config` 的配置命名空间。
- 学习示例 01–09 的 `Runtime[Configuration]` + `context_schema`。
- 主图、supervisor 子图、researcher 子图的 context 传递。

### 仍然使用的运行控制能力

- `RunnableConfig`：调用方可用它传递 callbacks、tags、metadata、`thread_id` 和 `recursion_limit`，但当前业务节点不读取它。
- 工具函数：直接接收 `Configuration`，需要持久化时接收 `runtime.store`。
- `Configuration.from_runnable_config()` 和 `_runtime_inputs()`：已删除，不能作为新调用或工具函数入口。
- 手写 supervisor/researcher 工具循环：它是当前项目的核心学习对象。
- `langchain_core.messages` 等底层导入：这些 API 仍然有效；改成更短的 `langchain.messages` 属于风格迁移，不会解决弃用问题。

## 7. 升级后的验证清单

先做不产生模型费用的检查：

```bash
uv run python -m compileall -q docs/langgraph-learning/examples
uv run python -c 'from open_deep_research.deep_researcher import deep_researcher; print(type(deep_researcher).__name__)'
```

再运行新版上下文案例：

```bash
uv run python docs/langgraph-learning/examples/09_runtime_context.py
```

它会发起一次真实模型调用。重点观察：

- 没有 `config_schema` 弃用警告；
- 节点从 `runtime.context` 读取 `Configuration`；
- 主图和两个子图都能接收并传递同一个 context；
- 模型字段位于 `configurable`，追踪标签位于顶层；
- 返回结果仍然由 `MessagesState` 追加消息。

## 8. 检查题

1. `input_schema` 和 `context_schema` 分别约束什么？为什么不能互换？
2. 如果只把 `config_schema=Configuration` 改成 `context_schema=Configuration`，但节点仍只接收 `config: RunnableConfig`，运行时配置是否真的迁移完成？
3. `with_config` 中 `tags` 为什么不应该放在 `configurable` 里？
4. 当前项目为何让 `RunnableConfig` 只保留运行控制职责，而节点统一使用 `Runtime[Configuration]` 读取业务配置？
5. 哪些场景适合直接使用 `create_agent`，哪些场景需要 `StateGraph`？
6. 如果把 API Key 放入 `Runtime.context`，还需要注意哪些日志、Store 和 LangSmith 脱敏边界？
