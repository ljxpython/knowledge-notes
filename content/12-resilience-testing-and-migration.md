# 第 12 章：容错、测试、评估与升级判断

研究 Agent 失败并不罕见。真正要学习的是：哪些失败可以缩短上下文后重试，哪些失败应保留证据并终止，哪些问题属于当前实现的风险而不是“模型不够聪明”。

## 1. 三层恢复策略

### 结构化输出重试

`clarify_with_user` 和 `write_research_brief` 使用：

```python
.with_structured_output(...)
.with_retry(stop_after_attempt=configurable.max_structured_output_retries)
```

这处理的是瞬时网络错误、提供商短暂错误或结构化解析失败。它不保证模型一定做出正确业务判断，重试次数也不应无限增加。

### 单页摘要降级

Tavily 结果的每个网页由 `summarize_webpage` 处理：

```python
summary = await asyncio.wait_for(model.ainvoke(...), timeout=60.0)
```

60 秒超时或摘要异常时，函数记录 warning 并返回原始网页内容。它的取舍是“保持研究可继续”优先于“每页都必须压缩成功”；代价是后续上下文可能变大。

### 上下文超限恢复

`compress_research` 最多尝试 3 次。若 `is_token_limit_exceeded` 判断为上下文过长，则调用：

```python
researcher_messages = remove_up_to_last_ai_message(researcher_messages)
```

它从尾部找到最后一个 `AIMessage`，返回该消息之前的历史。此做法很小，但语义是舍弃最近一次工具回合及其后续上下文，并非“精确按 token 截断”。

`final_report_generation` 的策略不同：首次按模型上下文上限近似为字符数截断 `findings`，后续每次再缩短 10%。它只缩短报告输入，不破坏原始 `raw_notes`。

## 2. token 限制检测的边界

`is_token_limit_exceeded` 通过异常类型、模块名、错误码与关键字识别 OpenAI、Anthropic、Gemini 的上下文超限。它不是通用异常分类器：

- 不认识新提供商的异常，就不会触发截断。
- 错误文本变化可能让检测失效。
- `MODEL_TOKEN_LIMITS` 需要维护。

当前默认 `openai:gpt-5.5` 不在 `MODEL_TOKEN_LIMITS`。因此最终报告遇到 token limit 时，`get_model_token_limit` 可能返回 `None`，项目会返回一条要求更新模型映射的错误报告，而不是自动截断。学习时把这当成待验证风险，不要假设默认模型一定能走恢复分支。

## 3. 当前最值得读懂的失败路径

`supervisor_tools` 包着 researcher 并发调用：

```python
try:
    tool_results = await asyncio.gather(*research_tasks)
except Exception as e:
    if is_token_limit_exceeded(e, configurable.research_model) or True:
        return Command(goto=END, update={...})
```

`or True` 使条件永远成立。结果是任意 researcher 子图异常都会结束整个研究阶段，并把已有 supervisor tool 消息转成 `notes`。这不是“只处理 token 超限”，而是一个广义的静默降级。

学习结论：

1. 它避免了一项子任务崩溃拖垮整张图。
2. 它丢失了异常详情，也不会给失败子题生成可见的 `ToolMessage`。
3. 修复前要明确产品策略：一项失败是继续其他任务、重试失败任务，还是结束报告。

不要为了让测试绿而随手删除 `or True`。那会改变用户可见行为，应先写一条复现异常的测试并约定预期。

## 4. 并发不是容错

本项目有两层 `asyncio.gather`：

| 位置 | 并发对象 | 风险 |
| --- | --- | --- |
| `supervisor_tools` | 多个 researcher 子图 | 一个子图异常会令 `gather` 抛异常 |
| `researcher_tools` | 一条消息中的多个本地工具 | `execute_tool_safely` 把异常转成文本结果 |
| `tavily_search` | 多个搜索 query | 异常默认向上抛出 |
| `tavily_search` 摘要 | 多个网页摘要 | 单页摘要内部超时/异常降级为原文 |

相同的 `gather`，因为调用前后有没有异常包装，表现完全不同。读并发代码时，先找“异常在哪一层被转换”。

## 5. 测试层次

| 层次 | 本项目例子 | 验证什么 | 是否需要真实模型 |
| --- | --- | --- | --- |
| 导入/编译 | `compileall`、导入 `deep_researcher` | 语法、依赖、图可构造 | 否 |
| 单元行为 | reducer、配置、工具选择 | 确定性逻辑 | 否 |
| 真实 Agent 最小调用 | 第 1–8 章 examples | 提供商协议、模型、工具消息链 | 是 |
| 评估 | `tests/run_evaluate.py` | 报告质量、相关性、完整性等 | 是，且会搜索 |
| 专项评估 | `tests/supervisor_parallel_evaluation.py` | 首轮 supervisor 调用的并行度 | 是 |

`tests/run_evaluate.py` 使用 LangSmith 数据集 `Deep Research Bench`，每次 target 都用 `MemorySaver`、新 `thread_id` 和可配置模型/搜索参数调用完整图。它属于线上式评估，不能当成无成本的本地单元测试。

本仓库现有 `src/legacy/tests/test_report_quality.py` 会在 pytest 收集期因缺少 `--research-agent` 参数失败。这是 legacy 测试基础设施问题，不是当前 `src/open_deep_research` 主实现的回归；做本课程文档时不修改它。

## 6. 升级到当前 LangGraph API 时的策略

旧版本主源码使用：

```python
StateGraph(..., input=..., output=..., config_schema=...)
```

当前文档倾向：

```python
StateGraph(
    OverallState,
    input_schema=InputState,
    output_schema=OutputState,
    context_schema=Context,
)
```

迁移原则：

1. 先锁住目前可运行的依赖与行为，升级前后各跑导入、章节真实调用和目标评估。
2. 先替换 `input`/`output` 为 `input_schema`/`output_schema`，不在同一变更中改状态结构或 prompts。
3. `config_schema` 不要机械改名；需要显式业务上下文时，改为 `context_schema` 并把节点签名改为 `Runtime[Context]`。
4. `RunnableConfig` 仍保留给 callbacks、tags、metadata、`thread_id` 等运行控制；业务配置统一放入 `Runtime.context`。新旧 API 的边界见第 [14 章](/knowledge-notes/docs/langgraph-langchain/14-current-api-migration/)。
5. 观察流式输出：输入/输出 schema 不自动隐藏 `stream_mode="values"` 里的内部通道。

## 7. 最小验证命令

```bash
uv run python -m compileall -q docs/langgraph-learning/examples
uv run python -c 'from open_deep_research.deep_researcher import deep_researcher; print(deep_researcher)'
uv run python docs/langgraph-learning/examples/08_integrated_mini_researcher.py
```

最后一条会调用真实模型并产生费用。完整 pytest 与 LangSmith evaluation 应在修复 legacy 收集问题、准备好搜索密钥和可控预算后再执行。
