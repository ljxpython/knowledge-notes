## Context

当前站点通过 `content/`、`content.manifest.json` 和 `scripts/prep-content.mjs` 生成 Astro 内容集合。`scripts/import-learning-content.mjs` 只支持一个已过时的合并目录、13 个固定文档，并把示例代码链接到远程 GitHub；站点没有本地源码资源入口。

目标源有三类：Open Deep Research 的 LangGraph 学习文档、LangChain v1 文档，以及 `langgraph_teach` 中 Deep Agents 教程。后者的工作目录包含依赖、缓存和运行产物，导入必须以 Git 跟踪文件为边界。

## Goals / Non-Goals

**Goals:**

- 生成三个可独立浏览的知识集合：现有 LangGraph/LangChain 集合、LangChain v1 集合、Deep Agents 集合。
- 保持现有 13 篇 LangGraph 文档的 URL 不变，并补齐第 14、15 章。
- 为所有导入文档生成稳定、全局唯一的 ID、顺序、章节和来源 URL。
- 在站内提供教学示例源码的静态查看链接。
- 让导入、链接重写、资源存在性和构建验证可重复执行。

**Non-Goals:**

- 不执行 Python、TypeScript、MCP、搜索、模型、数据库或前端服务示例。
- 不把 Deep Agents 的 workspace、依赖目录、日志、缓存、数据库和生成文件纳入知识库。
- 不新增 CMS、数据库、运行时 API 或在线代码执行沙箱。
- 不重写现有 Astro 页面布局，也不在本变更中重构无关内容。

## Decisions

### 1. 一个通用导入器，使用显式 source 配置

将固定 `chapters` 表改为来源配置：每个来源声明本地根目录、远程仓库、文档 glob、示例 glob、collection 元数据和 ID 前缀。导入器按配置读取 Markdown，生成 manifest，并复制源码资源。

选择配置驱动而不是三个独立脚本，是为了避免重复的文件读取、manifest 生成和链接处理逻辑；不引入新的配置文件格式，优先使用现有 JavaScript 模块常量和命令行参数。

### 2. 保留旧 LangGraph collection ID

现有 collection ID `langgraph-langchain` 和 13 个文档 slug 保持不变；只修正源 URL、补充第 14、15 章，并新增单独的 `langchain-v1` 和 `deep-agents` collection。这样不会破坏已发布的文档链接，也避免把两个不同学习路线强行压成一条 prev/next 链。

### 3. Deep Agents 只导入 Git 跟踪的教学文件

导入器使用 `git -C <repo> ls-files` 得到候选文件，再筛选 `*/docs/*.md` 和教学源码扩展名（`.py`、`.ts`、`.tsx`、`.js`、`.mjs`）。不扫描整个工作目录，因此不会把 `node_modules`、workspace、`.logs` 或本地生成物带入静态站。

### 4. 内容 ID 使用来源与主题命名空间

`content/` 当前是扁平目录，Deep Agents 各主题存在大量同名文件。生成 ID 时使用稳定前缀，例如 `deep-agents-backends-01-state-backend`，文件名和站内路由都使用该 ID；现有 13 个 ID 不变。文档的 `section` 字段保留主题分组，`order` 使用来源内显式顺序。

### 5. 示例代码复制到 public，并通过 resources 暴露

示例文件复制到 `public/examples/<collection>/<namespaced-path>`，文档 manifest 的 `resources` 增加“查看示例代码”链接。这样利用现有 `ResourceLinks.astro`，不增加代码渲染路由；浏览器可以直接查看静态源码，构建仍然只复制文件。

远程 source URL 继续保留，站内源码链接用于离线阅读，远程链接用于查看完整上游仓库和版本上下文。

### 6. 链接重写按源文件路径解析

链接处理必须区分外部 URL、站内文档、示例源码、上游项目源码和锚点。相对 `.md` 链接先基于源文件目录解析，再映射到目标文档 ID；相对代码链接映射到 public 示例或远程 source。无法解析的相对链接继续失败，并报告源文件与目标，避免静默生成坏链。

## Risks / Trade-offs

- [文档数量增加导致导航过长] → 使用 collection 和 `section` 分组；不新增复杂树形导航，先保持现有站点布局。
- [上游同名文件或新增文件造成 slug 变化] → 通过主题前缀和稳定路径生成 ID，并增加重复 ID 测试。
- [源码中包含本地敏感信息] → 只读取 Git 跟踪文件，导入前排除密钥文件和运行目录；资源校验禁止未允许的扩展名。
- [静态源码资源缺少语法高亮] → 第一版使用浏览器原始文本链接；只有用户明确需要站内高亮/复制体验时再增加代码页面。
- [上游文档链接格式超出当前正则覆盖范围] → 用路径解析和明确错误测试替代当前仅匹配固定章节的逻辑。

## Migration Plan

1. 扩展导入器和测试，先对三个本地源目录做 dry-run/导入校验。
2. 生成新的 `content/`、`content.manifest.json` 和 `public/examples/`，确认旧 13 个路由仍然存在。
3. 执行 `npm test`、`npm run assets:check` 和 `npm run build`。
4. 若构建失败，删除本次生成的内容资源并恢复原 manifest；源目录不做任何修改。

## Open Questions

- Deep Agents 的 frontend 教程中，是否将已跟踪的 TS/JS 示例与 Python 示例同等发布；设计默认发布教学源码，排除依赖目录。
- 是否把各 collection 的 README 转换为集合描述，还是只保留现有 collection 页面；设计默认不生成重复 README 文档。
