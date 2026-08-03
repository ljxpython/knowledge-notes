# Knowledge Notes

这是一个多主题知识笔记静态展示站，基于 [knowledge-site-template](https://github.com/ljxpython/knowledge-site-template) 构建。当前内容分为三个 collection：Open Deep Research 的 LangGraph 工程实践、LangChain v1 Agent，以及 `langgraph_teach` 的 Deep Agents 教学。

内容源和上游仓库：

- [`open_deep_research/docs/langgraph-learning`](https://github.com/ljxpython/open_deep_research/tree/main/docs/langgraph-learning)
- [`open_deep_research/docs/langchain`](https://github.com/ljxpython/open_deep_research/tree/main/docs/langchain)
- [`langgraph_teach/deepagent_src`](https://github.com/ljxpython/langgraph_teach/tree/main/deepagent_src)

## 刷新内容

```bash
npm run import:course -- \
  /path/to/open_deep_research/docs/langgraph-learning \
  /path/to/open_deep_research/docs/langchain \
  /path/to/langgraph_teach/deepagent_src
npm run assets:check
npm test
npm run build
```

导入器只读取 Markdown 和 Git 跟踪的教学源码，复制内容、生成 manifest、发布 `public/examples/` 静态源码并重写链接。Deep Agents 源目录中的 `node_modules`、workspace、日志、缓存和运行产物不会导入。

站内文档路径按 collection 区分：`/docs/langgraph-langchain/`、`/docs/langchain-v1/` 和 `/docs/deep-agents/`。每篇文档底部的“相关资源”包含可直接打开的站内示例源码链接；上游文档链接仍保留在页面顶部。

导入使用三个本地 checkout 当前工作树（通常是 `HEAD`）的内容，不负责拉取或锁定上游 commit；manifest 中的远程链接固定指向各仓库 `main`。文档 ID 由来源主题和文件名生成，文件移动会产生新路由。指向未纳入静态站的项目源码或官方资料的链接会继续指向上游，站内源码资源只覆盖允许扩展名的 Git 跟踪教学文件。

## 阅读提示

文档中的命令属于读者手动运行的示例。部分命令需要 API Key、外部服务权限，或可能产生模型与搜索费用。导入、构建、测试、预览和部署只生成静态页面，不会执行 Python、TypeScript、`uv`、模型调用、搜索、MCP、数据库或前端服务命令。

## 本地预览

```bash
npm install
npm run dev
```

导入源文档

导入脚本需要显式传入源目录，也可以使用 `OPEN_DEEP_RESEARCH_DOCS` 环境变量。仓库内已包含生成后的 Markdown，普通构建和预览不需要源文档目录。

仓库地址：[github.com/ljxpython/knowledge-notes](https://github.com/ljxpython/knowledge-notes)。
