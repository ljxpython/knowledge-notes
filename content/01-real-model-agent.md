# 第 1 章：真实模型与消息

## 学习目标

跑通一个最小 Agent 闭环：`HumanMessage` 进入 `MessagesState`，图节点通过真实模型的 `ainvoke` 得到 `AIMessage`，再把它更新回图状态。

## 它是什么

LangChain 的消息对象把“谁说的话、说了什么、是否带工具调用”等对话语义统一起来，避免直接拼字符串。`init_chat_model` 创建可配置聊天模型；本项目在 `deep_researcher.py` 中用同一模式，让研究、压缩和报告节点按运行时配置选择模型。`ainvoke` 是异步的一次真实模型调用。

当前项目证据：

- `deep_researcher.py` 的 `configurable_model = init_chat_model(...)` 声明了可配置模型。
- `researcher()` 用 `research_model.ainvoke(messages)` 调用模型。
- `researcher()` 返回 `{"researcher_messages": [response]}`，把模型返回的 `AIMessage` 交给状态 reducer 合并。

## 最小真实 Agent

示例文件：[01_real_model_agent.py](/knowledge-notes/examples/langgraph-langchain/examples/01_real_model_agent.py)。

```python
graph = (
    StateGraph(MessagesState, context_schema=Configuration)
    .add_node("answer", answer)
    .add_edge(START, "answer")
    .add_edge("answer", END)
    .compile()
)
```

`MessagesState` 自带 `messages` 状态字段及消息 reducer。因此节点返回一个新消息：

```python
return {"messages": [response]}
```

最终状态仍保留最初的 `HumanMessage`，并追加模型产生的 `AIMessage`。这就是后续多轮 Agent、工具调用和子图上下文的基础。

## 逐行读 `answer` 节点

示例的核心不是 `main`，而是被图执行器调用的节点：

```python
async def answer(state: MessagesState, runtime: Runtime[Configuration]):
    settings = runtime.context
    model = configurable_model.with_config(
        {
            "configurable": {
                "model": settings.research_model,
                "max_tokens": 80,
            },
            "tags": ["langsmith:nostream"],
        }
    )
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}
```

LangGraph 负责调用该函数。你不需要，也不应该自己写 `answer(state, runtime)`；当图运行到 `"answer"` 节点时，框架会注入 `Runtime`。调用图时通过 `context=Configuration(...)` 传入业务配置。

### `state: MessagesState`

`state` 是**当前节点看到的图状态快照**，不是 HTTP request，也不是模型对象。这里选 `MessagesState`，表示状态至少有一个 `messages` 字段，并且它带有 LangGraph 内置的消息 reducer。

| 本例用法 | 含义 | 不能做什么 |
| --- | --- | --- |
| `state["messages"]` | 读取到目前为止的完整会话消息，包括输入的 `HumanMessage` | 不能把它当成单个字符串直接 `.lower()` |
| `await model.ainvoke(state["messages"])` | 将消息列表交给聊天模型，模型可识别每条消息的角色 | 不能期望模型自动看到其他 state 字段 |
| `return {"messages": [response]}` | 返回**局部 state update**；reducer 将 `AIMessage` 追加到旧消息 | 不应原地执行 `state["messages"].append(response)` 后返回整个 state |

数据变化如下：

```text
图输入：
messages = [HumanMessage("只用一句中文说明 LangGraph 的作用。")]

answer 返回：
{"messages": [AIMessage("LangGraph ...")]}

MessagesState reducer 合并后的图状态：
messages = [
  HumanMessage(...),
  AIMessage(...),
]
```

节点不必接收整个 `MessagesState`。例如后面的 researcher 节点会接收 `ResearcherState`，因为它还需要 `research_topic`、工具循环次数等业务字段。**参数类型要与该节点真正需要读的 state 对齐。**

### `runtime: Runtime[Configuration]` 与 `config: RunnableConfig`

当前节点通过 `runtime.context` 读取业务配置。当前主实现的业务节点只声明 `state` 和 `runtime`；只有新节点确实需要读取运行控制信息时，才额外声明 `config: RunnableConfig`。两者与 `state` 的边界很重要：

| 数据类型 | 放在哪里 | 本项目例子 | 是否应进入 prompt |
| --- | --- | --- | --- |
| 对话、研究结论、工具结果 | `state` | `messages`、`notes` | 由节点明确决定 |
| 模型选择、并发限制、feature flag | `Runtime.context` | `runtime.context.research_model` | 默认不会 |
| thread 标识 | `RunnableConfig` | `configurable.thread_id` | 默认不会 |
| 追踪与回调信息 | `RunnableConfig` | `tags`、`metadata`、`callbacks` | 默认不会 |

### `runtime: Runtime[Configuration]` 是什么 Python 语法

它是**带泛型参数的变量类型注解**，可拆成三部分：

```python
async def answer(
    state: MessagesState,
    runtime: Runtime[Configuration],
):
    settings = runtime.context
```

| 片段 | Python 含义 | 在本项目中的含义 |
| --- | --- | --- |
| `runtime` | 参数名，函数体内正常使用的变量名 | LangGraph 注入的运行时对象 |
| `:` | 类型注解语法，不是赋值、不是继承 | 告诉读者、IDE 和类型检查器参数类型 |
| `Runtime[...]` | `Runtime` 是泛型类，方括号为它指定类型参数 | 表示该 Runtime 的 context 预期类型 |
| `Configuration` | 类型参数，不是构造函数调用 | `runtime.context` 应按 `Configuration` 的属性使用 |

所以它**不是**下面两种写法：

```python
# 错误理解 1：不要在节点内手动创建 Runtime。
runtime = Runtime[Configuration]()

# 错误理解 2：方括号不是把 Configuration 传给 Runtime 的运行时函数调用。
Runtime(Configuration)
```

正确的数据流是调用方创建业务 context，LangGraph 在执行节点时把 Runtime 对象作为参数注入：

```python
context = Configuration(search_api="none")
await graph.ainvoke(graph_input, context=context)

# 节点执行时，框架等价于调用：
# await answer(current_state, injected_runtime)
# injected_runtime.context is context
```

`Runtime[Configuration]` 主要给静态类型检查器和 IDE 提供信息：Pyright、mypy 或编辑器能推断 `runtime.context.research_model`、`runtime.context.search_api` 等属性。它不会替代 Pydantic 校验，也不会自动把普通字典转换为 `Configuration`。因此调用入口必须传 `Configuration(...)`、`Configuration.from_env()`，或先用 `Configuration.model_validate(raw_context)` 校验外部字典。

运行时仍可用普通 Python 的注解检查工具观察它：

```python
from typing import get_type_hints

hints = get_type_hints(answer)
assert hints["runtime"] == Runtime[Configuration]
```

这里断言的是函数声明的类型信息，不会创建图、调用模型或修改 `runtime.context`。

### 读懂 LangGraph 的 `Runtime` 定义

LangGraph 源码中的 `Runtime` 可简化为下面的形状：

```python
@dataclass(**_DC_KWARGS)
class Runtime(Generic[ContextT]):
    context: ContextT = field(default=None)  # type: ignore[assignment]
    """Static context for the graph run, like `user_id`, `db_conn`, etc."""

    store: BaseStore | None = field(default=None)
```

这段代码定义的是**框架运行时对象的蓝图**。项目节点只读取框架注入的对象：`runtime.context` 取本次运行依赖，`runtime.store` 取长期存储；不要在节点内自行创建或替换它。

#### 1. `@dataclass(**_DC_KWARGS)`：给类自动生成初始化逻辑

`@decorator` 是 Python 装饰器语法。类体执行完成后，Python 会把类对象交给装饰器，并重新绑定同名变量。下面两段等价：

```python
@dataclass(**_DC_KWARGS)
class Runtime:
    ...
```

```python
class Runtime:
    ...

Runtime = dataclass(**_DC_KWARGS)(Runtime)
```

`dataclasses.dataclass` 会依据带类型注解的字段生成 `__init__`、`__repr__`、相等比较等样板代码。因此可以用关键字参数构造一个简化的普通 dataclass：

```python
runtime = Runtime(context=settings, store=store)
```

`**_DC_KWARGS` 是**字典展开为关键字参数**。例如：

```python
options = {"kw_only": True}
Runtime = dataclass(**options)(Runtime)
# 等价于：Runtime = dataclass(kw_only=True)(Runtime)
```

`_DC_KWARGS` 的前导下划线表示 LangGraph 的内部实现细节。学习时应理解它把一组 dataclass 选项传入装饰器，不应依赖其当前具体内容；版本升级时这些内部选项可以变化。

#### 2. `Generic[ContextT]`：把 context 类型延后交给使用者指定

`ContextT` 是 `TypeVar`（类型变量），`Generic[ContextT]` 声明 `Runtime` 是一个泛型类。它类似“容器内元素类型尚未固定”的承诺：

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class Box(Generic[T]):
    def __init__(self, value: T):
        self.value = value

text_box: Box[str] = Box("hello")
number_box: Box[int] = Box(42)
```

同理，`Runtime[Configuration]` 表示“这个 Runtime 的 `context` 按 `Configuration` 使用”。`Generic[...]` 服务于类型检查和 IDE 补全；Python 运行时不会因为写了 `Runtime[Configuration]` 就自动实例化 `Configuration` 或校验字典。

#### 3. `context: ContextT = field(default=None)`：注解、默认值与类型检查例外

这一行同时有三层含义：

```python
context: ContextT = field(default=None)
```

1. `context` 是实例属性名。
2. `: ContextT` 是静态类型声明。参数化为 `Runtime[Configuration]` 后，IDE 可把它推断为 `Configuration`。
3. `field(default=None)` 告诉 dataclass：未提供 `context` 时默认值是 `None`。`field(...)` 比直接写 `= None` 更通用，未来可设置 `default_factory`、`repr`、`init` 或 metadata；这里的 `None` 不可变，直接默认值是安全的。

`None` 不能按严格静态类型赋给 `ContextT`，所以源码紧跟 `# type: ignore[assignment]`。这是给 mypy/Pyright 的定点豁免，**不是 Python 运行时的注释，也不会改变实际值**。它表达的框架事实是：图构建或某些内部执行阶段可能暂时没有 context；对本项目而言，节点一旦读取业务配置，就要求调用方传入 `context=Configuration(...)`。

如果你自己定义 Runtime 类，应让声明准确反映 `None` 的可能性：

```python
@dataclass
class DemoRuntime(Generic[ContextT]):
    context: ContextT | None = None
```

#### 4. `store: BaseStore | None`：PEP 604 联合类型

`A | B` 是 Python 3.10+ 的联合类型语法，等价于旧写法 `Optional[A]` 或 `Union[A, None]`：

```python
store: BaseStore | None
# 等价于：store: Optional[BaseStore]
```

它表示 `store` 可能是一个实现 `BaseStore` 接口的对象，也可能是 `None`。项目中的 MCP token 辅助函数把 `runtime.store` 显式传入：

```python
tools = await get_all_tools(runtime.context, runtime.store)
```

未配置 Store 的简单图中它可以是 `None`；需要跨运行保存 token、用户偏好或其他数据时，在编译图时配置 Store：

```python
store = InMemoryStore()
graph = StateGraph(State, context_schema=Configuration).compile(store=store)
result = await graph.ainvoke(graph_input, context=Configuration(...))
```

业务代码不该把 Store 塞进 state，更不能把 Store 对象交给模型。

#### 5. 三者连起来看

```text
图编译：compile(store=某个 BaseStore 实现)  # 可选
调用执行：ainvoke(..., context=Configuration(...))
                 |
                 v
LangGraph 创建并注入 Runtime[Configuration]
                 |
                 +--> runtime.context.research_model
                 +--> runtime.store
```

`Runtime[Configuration]` 是节点签名中的类型契约；真正传递对象的是 `graph.ainvoke(..., context=...)` 与 LangGraph 执行器。你的节点只需要读取，不需要复刻 LangGraph 的 `Runtime` dataclass。

当前推荐的读取链路是：

```text
graph.ainvoke(input, context=Configuration(...), config=...)
  -> LangGraph 把 Runtime 注入 answer(...)
  -> runtime.context
  -> settings.research_model
```

第 1 章的 `main()` 使用 `context=Configuration.from_env()`。如果要覆盖配置，直接构造 Pydantic context：

```python
result = await graph.ainvoke(
    {"messages": [HumanMessage(content="一句话解释 LangGraph。")]},
    context=Configuration(
        research_model="openai:gpt-5.5",
        research_model_max_tokens=80,
    ),
    config={
        "tags": ["learning", "chapter-01"],
        "metadata": {"lesson": "01"},
    },
)
```

这里 `context` 承载业务配置，`config` 只承载 LangChain/LangSmith 的追踪控制。不要把 API Key 放进 `metadata`、state 或 prompt。请求级密钥需要由受信任入口放进 `Configuration.api_keys`，详见第 [11 章](/knowledge-notes/docs/langgraph-langchain/11-configuration-security-and-runtime/)。

### `RunnableConfig` 只负责运行控制

`RunnableConfig` 是 Python 的 `TypedDict` 类型提示，不需要自行实例化。当前项目不从它构造 `Configuration`，也不把模型、搜索、MCP 或密钥放进去；这些都由 `Runtime.context` 提供。

新代码从环境变量创建 context 时使用：

```python
context = Configuration.from_env()
result = await graph.ainvoke(graph_input, context=context)
```

需要覆盖单次运行配置时，使用 `model_copy(update=...)` 或直接构造 `Configuration(...)`。图调用中的 `config` 只传运行控制字段：

```python
result = await graph.ainvoke(
    graph_input,
    context=Configuration(research_model="openai:gpt-5.5"),
    config={
        "configurable": {"thread_id": "lesson-01"},
        "tags": ["learning", "chapter-01"],
        "metadata": {"lesson": "01"},
        "recursion_limit": 25,
    },
)
```

调用 `graph.invoke(input, config=...)` 或 `graph.ainvoke(input, config=...)` 时，常见的标准顶层字段如下：

| 顶层字段 | 类型 | 谁消费 | 本项目中的意义 |
| --- | --- | --- | --- |
| `configurable` | `dict[str, Any]` | 模型的 configurable fields、checkpointer | 放 `thread_id`；模型字段只在 `with_config` 中使用 |
| `tags` | `list[str]` | LangChain/LangSmith | 追踪分类，可继承给子调用 |
| `metadata` | `dict[str, Any]` | LangChain/LangSmith | 追踪附加信息，不应放密钥 |
| `callbacks` | callback 或列表 | LangChain | 日志、流式、观测回调 |
| `run_name` | `str` | LangChain | 当前运行的追踪名称 |
| `max_concurrency` | `int` | LangChain Runnable 批处理 API | 限制 `batch()` 类 API 的并发，不等于本项目 researcher 并发数 |
| `recursion_limit` | `int` | LangGraph | 防止图无限循环 |
| `run_id` | UUID | LangChain | 指定追踪运行 ID，通常不手写 |

业务配置必须在调用入口构造成 `Configuration`。`context_schema=Configuration` 只声明类型通道，不会自动把普通字典校验成 Pydantic 对象，因此不要写 `context={"research_model": ...}`；使用 `Configuration(...)` 或 `Configuration.model_validate(raw_context)`。

#### 两组最容易混淆的并发/配置字段

```python
config = {
    "max_concurrency": 8,
    "configurable": {
        "max_concurrent_research_units": 2,
    },
}
```

- `max_concurrency=8` 是 LangChain Runnable 的批处理并发设置。
- `max_concurrent_research_units=2` 是本项目在 `supervisor_tools` 中切片 `ConductResearch` 调用并传给 `asyncio.gather` 的业务上限。

它们名字相近、作用层次不同，不能互相替代。

#### `context_schema=Configuration` 与当前版本

项目主图当前使用：

```python
StateGraph(
    AgentState,
    context_schema=Configuration,
    input_schema=AgentInputState,
)
```

旧代码中的 `config_schema` 已在 LangGraph v1 进入弃用路径，未来会移除；当前实现已删除该参数。新节点应使用 `Runtime[Configuration]` 读取 `runtime.context`，并在调用入口显式传入 `context=Configuration(...)`。

因此当前学习和调用项目时：

- 新代码使用 `context=Configuration(...)` 传入业务字段。
- 节点使用 `runtime: Runtime[Configuration]`，从 `runtime.context` 读取配置。
- `RunnableConfig` 只放 `thread_id`、callbacks、tags、metadata、recursion_limit 等运行控制。
- 旧平台必须迁移为 `context=Configuration(...)`；旧 API 的差异与原因见第 [14 章](/knowledge-notes/docs/langgraph-langchain/14-current-api-migration/)。

#### 不调用模型的配置验证

下面的命令只构造并解析 Pydantic 配置，不会发起模型、搜索或 MCP 请求：

```bash
uv run python -c '
from open_deep_research.configuration import Configuration

settings = Configuration(
    research_model="openai:gpt-5.5",
    search_api="none",
    max_concurrent_research_units=2,
)
assert settings.research_model == "openai:gpt-5.5"
assert settings.search_api.value == "none"
assert settings.max_concurrent_research_units == 2
print("配置解析成功")
'
```

### 节点可以有哪些参数

对于本项目当前使用的 Graph API，最常见的节点签名是：

| 签名 | 适用场景 | 本项目/课程位置 |
| --- | --- | --- |
| `def node(state)` | 纯本地、同步状态转换 | 第 2 章 `finish` |
| `async def node(state)` | 要 `await` 异步 I/O，但不需要读取运行配置 | 简单异步工具或本地 I/O |
| `def node(state, config: RunnableConfig)` | 同步节点确实需要读取 `thread_id`、callbacks 等运行控制 | 较少见的控制节点 |
| `async def node(state, runtime: Runtime[Context])` | 异步模型/工具调用且需要业务 context | 本例 `answer`、项目主实现的各 Agent 节点 |
| `async def node(state, runtime: Runtime[Context], config: RunnableConfig)` | 同时需要业务 context 和运行控制 | 只有实际读取控制字段时才加 |

`state` 是节点的业务输入；`runtime.context` 是业务配置；`config` 是运行控制面。**不要为了“参数齐全”而无条件加 `config`**：当前示例的模型节点只接收 `state` 和 `runtime`。

> 本项目运行在 Python 3.11+。节点内直接 `await model.ainvoke(state["messages"])`；不为了透传业务配置再声明 `RunnableConfig`。需要跨版本手动处理回调传播时，按目标 LangChain 版本的官方文档单独验证。

## `configurable_model.with_config(...)` 到底做了什么

先看模型的创建：

```python
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)
```

这不是某一个固定的 OpenAI 模型，而是一个 `_ConfigurableModel`。它声明了三个允许在运行时绑定的**模型字段**：

| 字段 | 本例来源 | 实际作用 | 注意点 |
| --- | --- | --- | --- |
| `model` | `settings.research_model` | 选择 provider 与模型，例如 `openai:gpt-5.5` | 前缀决定 provider；不要只写不带 provider 的猜测名称 |
| `max_tokens` | 常量 `80` | 限制本次输出的 token 预算 | 不是输入上下文上限，也不保证任何模型都严格遵守相同语义 |
| `api_key` | `get_api_key_for_model(...)` | 传给对应 provider 的认证信息 | 可以为 `None`；不要打印、写入 state 或 metadata |

接着：

```python
model = configurable_model.with_config(
    {
        "configurable": {
            "model": settings.research_model,
            "max_tokens": 80,
            "api_key": ...,
        },
        "tags": ["langsmith:nostream"],
    }
)
```

`with_config` **返回一个带默认配置的新 Runnable，不修改**全局的 `configurable_model`。因此同一个基础模型可以在项目不同节点生成不同派生对象：

```text
configurable_model
  ├─ with_config(research_model + research_model_max_tokens)
  ├─ with_config(compression_model + compression_model_max_tokens)
  └─ with_config(final_report_model + final_report_model_max_tokens)
```

传入字典中的字段分两类：

1. 已在 `configurable_fields` 声明的 `model`、`max_tokens`、`api_key`，放在 `configurable` 下成为这次派生模型的默认模型参数。
2. 标准 `RunnableConfig` 字段，例如 `tags`、`metadata`、`callbacks`、`run_name`，放在顶层控制追踪与执行观测。`tags` 会传递给子 Runnable，便于在 LangSmith 中筛选；本项目的 `langsmith:nostream` 是项目约定标签，不是 Python 异步开关。

这与下面两个 API 不同：

| API | 绑定的东西 | 本项目中的角色 |
| --- | --- | --- |
| `with_config(...)` | Runnable 的运行/模型配置、追踪信息 | 为每个节点选择模型和 token 预算 |
| `bind_tools([...])` | 模型可调用的工具定义 | 第 4、5 章将工具协议交给模型 |
| `invoke(..., config=...)` / `ainvoke(..., config=...)` | 单次调用的输入与可选覆盖配置 | 实际发起模型请求 |

不要在每次调用前修改全局 `configurable_model`。它被 `deep_researcher.py` 多个节点复用；就地修改会让并发 researcher 彼此串配置。`with_config` 生成派生 Runnable 正是为了避免这个问题。

## 为什么 `main` 和节点都用了 `async`

本例真正需要异步的是：

```python
response = await model.ainvoke(...)
result = await graph.ainvoke(...)
```

远程模型请求是 I/O 等待。`async def` 允许事件循环在等待网络响应时处理其他任务；第 6 章多个 researcher 子图的 `asyncio.gather` 才能并发等待多个请求。

`async def main()` 不是唯一写法，但函数体内有 `await` 时它必须是异步函数。文件末尾的：

```python
if __name__ == "__main__":
    asyncio.run(main())
```

负责从普通 Python 脚本启动事件循环并等待 `main()` 完成。

### 可以写成 `def main()` 吗

可以，分两种情况。

**方案一：仅让入口同步，节点和图仍保持异步。** 这是最小改动，适合 CLI 脚本：

```python
async def async_main():
    result = await graph.ainvoke({"messages": [HumanMessage(content="你好")]})
    print(result["messages"][-1].content)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
```

**方案二：整条调用链都改同步。** 同步节点用 `def`，同步模型/图 API 使用 `invoke`：

```python
def answer(state: MessagesState, runtime: Runtime[Configuration]):
    settings = runtime.context
    model = configurable_model.with_config(
        {
            "configurable": {
                "model": settings.research_model,
                "max_tokens": 80,
            },
            "tags": ["langsmith:nostream"],
        }
    )
    response = model.invoke(state["messages"])
    return {"messages": [response]}


def main():
    graph = (
        StateGraph(MessagesState, context_schema=Configuration)
        .add_node("answer", answer)
        .add_edge(START, "answer")
        .add_edge("answer", END)
        .compile()
    )
    result = graph.invoke(
        {"messages": [HumanMessage(content="只用一句中文说明 LangGraph 的作用。")]},
        context=Configuration.from_env(),
    )
    print(result["messages"][-1].content)
```

同步版更容易在一次性命令行脚本中阅读，但会阻塞当前线程，不能利用 `asyncio.gather` 并发等待多个模型或工具请求。更重要的是，**图中只要有一个 async 节点，就必须从 `graph.ainvoke(...)` / `graph.astream(...)` 进入；不能用 `graph.invoke(...)` 强行执行 coroutine 节点。**

在 Jupyter、IPython、FastAPI 等已有事件循环的环境中，不能再调用 `asyncio.run(...)`；直接使用：

```python
result = await graph.ainvoke(...)
```

## 本节最小检查

不产生外部模型调用的静态检查：

```bash
uv run python -m compileall -q docs/langgraph-learning/examples/01_real_model_agent.py
```

真实模型验证仍使用：

```bash
uv run python docs/langgraph-learning/examples/01_real_model_agent.py
```

它会调用配置的模型并产生 token 费用；不会调用搜索或 MCP。

## 运行

```bash
uv run python docs/langgraph-learning/examples/01_real_model_agent.py
```

预期现象：终端输出一行模型回复，内容是对“LangGraph 的作用”的简短说明。调用只使用本地模型配置，不调用搜索、MCP、数据库或项目的完整深度研究图。

脚本会用 `python-dotenv` 读取仓库根目录的 `.env`，因此无需把密钥手工 export 到当前 shell；密钥不会被打印。

## 本次真实验证

已使用默认 `openai:gpt-5.5` 运行一次。模型返回：

```text
LangGraph 用于构建、编排和运行带有状态与循环控制的多步骤 AI Agent 工作流。
```

## 常见误区

**把 `ainvoke` 当成 Agent。** `ainvoke` 只是一次模型调用；本例之所以是最小 Agent，是因为模型调用被放进了可执行的 `StateGraph` 节点，并且读写了图状态。真正的工具型 Agent 会在后续章节加入 `bind_tools`、`ToolMessage` 和循环路由。

**直接传字符串就够了。** 很多模型接口接受字符串，但项目实际使用消息对象。工具调用时必须保留 `AIMessage.tool_calls` 和匹配的 `ToolMessage.tool_call_id`，字符串会丢掉这些协议语义。

**配置只能从环境变量读。** 新代码可使用 `Configuration.from_env()`，也可在受信任调用入口显式构造 `Configuration(...)` 作为 context。

**把 `with_config` 当成修改全局模型。** 它返回派生 Runnable；应保存返回值并调用这个返回值。全局 `configurable_model` 仍保持可被其他节点独立配置的状态。

**把 `asyncio.run()` 用在 Notebook 或 FastAPI 里。** 这些环境通常已有事件循环，会报“event loop is already running”。在 async 函数、Notebook 单元或 Web handler 中直接 `await graph.ainvoke(...)`。

## 检查题

1. 为什么 `return {"messages": [response]}` 不会删掉输入的 `HumanMessage`？
2. 若 `answer` 不读取模型配置、thread ID、callbacks，`config` 参数能否删除？为什么？
3. `max_tokens=80` 限制的是哪一部分 token？它和模型的 context window 有什么区别？
4. 在 `deep_researcher.py` 的 `researcher()` 中，为什么不能修改全局 `configurable_model` 后再调用 `ainvoke`？
5. 一个图有 async `answer` 节点时，为什么 `graph.invoke(...)` 不是同步改造方案？
6. 为什么 `max_concurrency` 不能替代 `max_concurrent_research_units`？
7. 为什么 `graph.ainvoke(input, {"research_model": "..."})` 不能代替 `graph.ainvoke(input, context=Configuration(...))`？
