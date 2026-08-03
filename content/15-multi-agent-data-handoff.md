# 第 15 章：主 Agent、子 Agent 与结构化数据交接

## 学习目标

读完本章，你应能回答四个问题：

1. 用户问题、用户画像、身份和密钥分别应该从哪里进入图？
2. 主 agent 怎样把一个问题拆成可执行的子任务？
3. 主 agent 与子 agent 为什么不直接共享整份 state，而要定义输入/输出契约？
4. 子 agent 的结果怎样以可验证、可汇总的格式回到主 agent？

本章对应当前项目的真实层级：主图 `deep_researcher`、supervisor 子图、researcher 子图。新案例把它缩小为“协调 agent -> 两个 researcher 子图 -> 协调 agent 汇总”，并使用真实模型调用。

## 1. 先分清四种数据

多 agent 系统最容易出错的地方不是模型，而是把不同生命周期的数据混在一起。

| 数据 | 正确位置 | 当前项目例子 | 是否应进入模型 prompt |
| --- | --- | --- | --- |
| 用户问题、用户明确允许使用的偏好 | 图输入和 graph state | `AgentInputState.messages` | 需要时明确拼入 |
| 研究简报、子任务、子 agent 发现、最终报告 | graph state 或子图 output | `research_brief`、`notes`、`compressed_research` | 由消费该字段的节点明确拼入 |
| 用户身份、模型选择、密钥、访问 token | `Runtime.context` | `Configuration.user_id`、`api_keys`、`supabase_access_token` | 默认不进入 |
| 跨运行的 token、用户偏好等长期数据 | `Runtime.store` | MCP token | 默认不进入 |

因此，“把用户信息传入图”需要先问：这条信息是否真的让模型看到？

```python
await graph.ainvoke(
    {
        # 可以进入 prompt 的最小信息。
        "user_question": "怎样设计多 agent 交接？",
        "user_profile": "Python 初学者，希望中文解释。",
    },
    # 仅供应用逻辑使用的运行依赖，不应原样拼入 prompt。
    context=Configuration(user_id="trusted-user-id"),
)
```

不要把 JWT、邮箱、完整 CRM 档案、API key 或 Supabase access token 写进 `user_profile`。`user_id` 用于鉴权、Store 命名空间或审计，除非业务明确需要，模型不需要知道它。

## 2. 当前项目的真实交接链

源码证据：

- [state.py](https://github.com/ljxpython/open_deep_research/blob/main/src/open_deep_research/state.py) 定义 `AgentInputState`、`AgentState`、`SupervisorState`、`ResearcherState` 和 `ResearcherOutputState`。
- [deep_researcher.py](https://github.com/ljxpython/open_deep_research/blob/main/src/open_deep_research/deep_researcher.py) 的 `write_research_brief`、`supervisor_tools`、`researcher`、`compress_research` 与 `final_report_generation` 完成交接。

真实调用链如下：

```text
调用者输入 {messages: [HumanMessage(用户问题)]}
  -> AgentInputState.messages
  -> clarify_with_user
  -> write_research_brief
       ResearchQuestion(research_brief=...)             # 结构化模型输出
  -> AgentState.research_brief
  -> supervisor_messages
  -> supervisor 模型调用 ConductResearch(research_topic=...)
       AIMessage.tool_calls                              # 工具协议中的结构化参数
  -> supervisor_tools 显式投影子图输入
       {researcher_messages, research_topic}
  -> researcher_subgraph
  -> compress_research
       {compressed_research, raw_notes}                 # ResearcherOutputState
  -> ToolMessage(content=compressed_research)
  -> SupervisorState.supervisor_messages
  -> AgentState.notes
  -> final_report_generation
  -> final_report
```

这里有两种不同的“交接格式”，不要混为一谈：

| 场景 | 格式 | 原因 |
| --- | --- | --- |
| supervisor 请求应用执行动作 | `AIMessage.tool_calls` + `ConductResearch` 参数 | 符合模型工具调用协议，结果必须回填匹配的 `ToolMessage.tool_call_id` |
| Python 节点直接调用 researcher 子图 | 普通 `dict` 输入 + `ResearcherOutputState` 输出 | 是图调用边界，不需要伪造模型工具消息 |

`supervisor_tools` 先从工具调用中取出 `research_topic`，再构造 researcher 子图所需字段。子图并不会自动看到 `SupervisorState`，这是刻意的边界控制。

## 3. 为什么必须显式投影输入

父 state 往往包含不属于子 agent 的字段，例如主对话历史、其他子任务的结果、密钥引用、内部路由计数。直接把整份 parent state 传给子图会产生三个问题：

1. **职责污染**：子 agent 不知道哪些字段是自己可读、可写的。
2. **上下文膨胀**：无关消息和其他子任务结果被带进 prompt，增加成本并干扰回答。
3. **数据泄露**：本不该给子 agent 或模型看的用户信息会顺带传播。

推荐在调用点建立一个小而稳定的投影：

```python
researcher_input = {
    "user_profile": state["user_profile"],
    "user_question": state["user_question"],
    "task": task,
}
result = await researcher_graph.ainvoke(
    researcher_input,
    context=runtime.context,
)
```

这段代码就是数据边界：只有 `ResearcherInput` 声明的字段可进入子图。`context=runtime.context` 只传运行依赖，不等于把它放进 `researcher_input` 或 prompt。

## 4. 用 Pydantic 模型固定交接格式

本项目的 `ConductResearch`、`ResearchQuestion`、`Summary` 都是 Pydantic `BaseModel`。第 15 章案例进一步把每一层交接都命名成模型：

```python
class Subtask(BaseModel):
    topic: str
    question: str
    expected_evidence: str


class Finding(BaseModel):
    topic: str
    answer: str
    evidence: list[str]
    limitation: str
```

`with_structured_output(ResearchPlan)` 约束主 agent 只能生成含两个 `Subtask` 的计划；`with_structured_output(Finding)` 约束每个子 agent 都返回相同字段。主 agent 汇总时不用猜测某段自然语言里哪里是结论、哪里是证据、哪里是不确定性。

```text
主 agent -- ResearchPlan[Subtask, Subtask] --> 两个 researcher
researcher A -- Finding --> 主 agent
researcher B -- Finding --> 主 agent
主 agent -- FinalAnswer --> 调用者
```

结构化输出不是“模型一定正确”的保证。它保证的是**形状**：字段缺失、类型不对或列表长度不满足限制时，模型调用会失败或重试，而不是把难以解析的自由文本悄悄传给下一层。事实准确性仍要靠工具、引用、评估和人工检查。

## 5. 输入 schema、内部 state 与 output schema

案例定义了三套契约：

```python
class UserInput(TypedDict):
    user_profile: str
    user_question: str


class ResearcherInput(TypedDict):
    user_profile: str
    user_question: str
    task: Subtask


class ResearcherOutput(TypedDict):
    finding: Finding
```

它们在构图中分别使用：

```python
researcher_graph = StateGraph(
    ResearcherState,               # 子图内部完整 state
    context_schema=Configuration,  # 本次运行依赖
    input_schema=ResearcherInput,  # 父图允许传入的字段
    output_schema=ResearcherOutput,# 子图返回给父图的字段
)
```

`input_schema` 不是模型 prompt 的自动过滤器，`output_schema` 也不是访问控制系统。它们首先是图 API 的数据契约。真正进入模型的内容仍由 `research_one()` 中的 `HumanMessage(content=...)` 决定，因此要只拼接最小必要字段。

## 6. 最小真实 Agent 案例

运行 [10_multi_agent_handoff.py](/knowledge-notes/examples/langgraph-langchain/examples/10_multi_agent_handoff.py)：

```bash
uv run python docs/langgraph-learning/examples/10_multi_agent_handoff.py
```

它会执行四次短模型调用：

1. 主 agent 根据 `user_profile` 和 `user_question` 生成 `ResearchPlan`。
2. 两个 researcher 子图并发生成各自的 `Finding`。
3. 主 agent 只根据 `ResearchPlan` 与 `Finding` 生成 `FinalAnswer`。

案例不使用搜索、MCP、数据库或用户真实身份；费用仅来自四次短模型调用。模型配置从 `Configuration.from_env()` 读取，`.env` 由 `load_dotenv()` 载入。

## 7. 跟当前项目相比，案例省略了什么

| 当前项目 | 第 15 章案例 | 省略原因 |
| --- | --- | --- |
| `messages` 与澄清循环 | `user_question` / `user_profile` 两个字段 | 聚焦数据契约，不展开对话状态 |
| `ConductResearch` 工具协议 | 主节点直接调用 compiled subgraph | 先区分图边界与工具协议 |
| 搜索、MCP、token 截断、重试 | 无外部工具的短模型调用 | 防止外部副作用掩盖交接结构 |
| `compressed_research` 文本交接 | `Finding` Pydantic 交接 | 更直观地展示格式化结果 |

生产代码选择 `ToolMessage(content=compressed_research)`，是因为 supervisor 与 researcher 的交接发生在**模型工具调用循环**中。若你直接在 Python 节点调子图，像本案例一样返回 `Finding` 字段更简单。两者都合理，关键是不要跨越协议边界。

## 8. 常见错误

### 把全部用户资料放入 state

错。state 可能被 checkpoint、流式输出或其他节点读取。只传模型回答需要的、经过脱敏的最小字段；身份和凭据放 `Runtime.context` 或受控 Store。

### 把普通字典当成“结构化结果”

`{"answer": "..."}` 可以运行，但没有模型校验、字段说明或 IDE 补全。跨 agent、跨团队或需要长期维护时，优先 `BaseModel` 并给 `Field(description=...)` 写清语义。

### 子 agent 直接修改父 state

子图没有父 state 的共享可变引用。让子图返回一个小 output，再由父节点决定怎样合并。这避免两个并发子 agent 竞争写同一个列表或覆盖对方数据。

### 把 `Runtime.context` 自动拼进 prompt

LangGraph 不会自动做这件事，且不应该这样做。代码必须显式选择 `user_profile`、`task` 等可见字段；`user_id`、`api_keys`、token 和 Store 永远不应通过 f-string 传给模型。

## 9. 检查题

1. 当前项目中 `ResearchQuestion.research_brief`、`ConductResearch.research_topic`、`ResearcherOutputState.compressed_research` 分别由哪个节点产生、由哪个节点消费？
2. 为什么 `run_researchers()` 要逐个构造 `ResearcherInput`，而不是 `researcher_graph.ainvoke(state)`？
3. 若要让子 agent 使用“回答应简洁”的用户偏好，应该放在 `user_profile`、`Configuration` 还是 `Store`？分别说明三种选择的条件。
4. 若 researcher 必须调用受权限保护的 MCP 工具，哪些字段仍绝对不能拼进 prompt？
5. 把案例的 `Finding.evidence` 改为需要 URL、标题和摘录的结构化引用对象，然后思考最终主 agent 怎样避免引用未经子 agent 支持的结论。

## 10. 验证记录

静态检查已通过：`uv run python -m compileall -q docs/langgraph-learning/examples` 与构图导入检查均成功。

真实模型验证已完成：

```bash
uv run python docs/langgraph-learning/examples/10_multi_agent_handoff.py
```

本次执行完成了一个 `ResearchPlan`、两个并发 `Finding` 和一个 `FinalAnswer` 的结构化输出调用链。没有触发 Tavily、MCP、数据库或其他外部工具；成本只来自四次短模型调用。模型的具体自然语言内容每次会变化，因此本记录只固定可复查的数据契约和外部副作用边界。
