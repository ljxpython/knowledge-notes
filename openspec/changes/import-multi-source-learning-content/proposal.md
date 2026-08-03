## Why

当前知识库只导入 Open Deep Research 的 13 篇 LangGraph 文档，导入脚本还依赖已经不存在的合并目录 `docs/langgraph-langchain-learning`。LangChain v1、LangGraph 后续章节和 `langgraph_teach/deepagent_src` 中的大量教学内容及示例代码无法在站内统一检索和阅读，需要建立可重复的多源导入边界。

## What Changes

- 扩展内容导入流程，分别接入 `open_deep_research/docs/langgraph-learning`、`open_deep_research/docs/langchain` 和 `langgraph_teach/deepagent_src`。
- 保留现有 LangGraph 文档路由，补齐第 14、15 章；新增 LangChain v1 与 Deep Agents 两个知识集合。
- 以 Git 跟踪文件为准导入 Deep Agents 教程，排除 workspace、日志、缓存、依赖和运行产物。
- 为跨目录文档生成稳定且不冲突的内容 ID，并重写站内文档、示例代码和源代码链接。
- 将教学示例代码复制为站内静态源码资源，并在对应文档中提供可见链接；构建过程不执行示例代码或外部服务调用。
- 增加导入、链接、重复 ID、示例资源和构建校验，更新内容刷新文档与来源说明。

## Capabilities

### New Capabilities

- `multi-source-learning-content`: 从多个本地教学源生成带集合元数据、稳定链接和站内示例源码的静态知识内容。

### Modified Capabilities

无。

## Impact

- 修改 `scripts/import-learning-content.mjs` 及其测试，可能拆分或重命名为通用多源导入器。
- 扩展 `content.manifest.json` 和 `content/` 内容生成结果；必要时调整 `scripts/prep-content.mjs` 的资源校验。
- 新增或更新 `public/examples/` 静态源码资源。
- 更新 `README.md`、导入命令、源仓库地址和构建验证说明。
- 不新增运行时依赖，不执行 Python 示例、模型调用、搜索、MCP 或数据库操作。
