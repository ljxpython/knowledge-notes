---
name: project-knowledge-import
description: 将外部或相邻仓库的技术学习文档、示例源码和内部链接转化为本项目的 Astro 知识库。用于新增或更新 docs 文档源、配置多仓库导入、复制公开示例、重写站内链接、按专题组织集合，或修复导入后文档、代码资源和集合页展示问题。
---

# 项目知识文档导入

将源仓库的 Markdown 讲义和静态示例转化为 `content/`、`public/examples/` 与 `content.manifest.json`，并保持可追溯来源、可用链接和清晰的学习导航。只展示内容，不执行导入的 Python、模型、MCP 或网络示例。

## 先确认范围

1. 阅读 `scripts/import-learning-content.mjs`、`content.manifest.json`、`src/content.config.ts` 与现有 collection 页面，确认当前数据契约和命名规则。
2. 明确每个源的文档根目录、仓库根目录、collection 标识、标题、来源 URL 和安全提示。
3. 先检查已有导入器能否覆盖需求；仅在新的源格式或展示行为需要时修改它。不要手工批量编辑生成的 `content/` 或 manifest。

## 导入流程

1. 在 `sourceDefaults` 添加源配置，保留 `sourceRepo`、`sourceDir`、`repoRoot`、collection 元数据和明确的 notice。
2. 用已跟踪文件扫描 Markdown 与允许的代码扩展名；文档 ID 必须稳定且跨源唯一，重复文件名应带目录命名空间。
3. 重写相对 Markdown 链接：文档指向 `/knowledge-notes/docs/...`，本地代码指向 `/knowledge-notes/examples/...`，其余仓库文件指向上游源码 URL。
4. 将允许的示例源码复制到 `public/examples/`，并注册为文档 resource；拒绝 `..`、不存在路径和未支持的相对链接。
5. Deep Agents 使用子目录作为 `section`：维护显式学习顺序，总览文档排在章节前，未知目录格式化后追加到末尾。
6. 运行 `node scripts/import-learning-content.mjs` 重新生成 manifest 和内容；生成后再修改源文档或导入规则，绝不反向修补产物。

## 集合与资源展示

- 首页以 collection 为入口，避免将全部文档一次平铺；需要首页预览时使用原生 `<details>` 折叠文档。
- 仅对 `deep-agents` 按 `section` 分组。复用 `src/components/TopicGroups.astro`，每个主题默认收起，展示标题、数量和组内排序；其他 collection 保持原有学习路径。
- Deep Agents 的上一篇/下一篇必须过滤到当前 section；其他 collection 保持 collection 内连续导航。
- `ResourceLinks.astro` 对站内 `/knowledge-notes/examples/` 资源使用 `readFileSync(..., 'utf8')` 内嵌代码，并复用正文 `pre` 的深色样式和横向滚动。解析路径时必须限制在 `public/` 下，外部资源仍保留普通链接。

## 验证闭环

按顺序执行：

```bash
npm test
npm run assets:check
npm run build
```

随后用浏览器检查首页、受影响 collection、含 resource 的文档和移动端：

- collection 数量、文档数量、主题顺序和总览优先级正确；
- Deep Agents 主题折叠/展开正常且不跨主题导航；
- 示例源码中的中文正常显示，代码块不撑破移动端；
- 非 Deep Agents collection 的布局和导航没有回归。

## 约束

- 不执行导入的示例代码，不启动服务，不调用模型、MCP、数据库或外部 API。
- 保持已有文档 ID、URL、来源链接和非目标 collection 行为；新增依赖前先确认现有脚本和 Astro 原生能力不够。
- 内容导入、前端展示和验证是同一个变更：任一环节失败时不要标记完成。
