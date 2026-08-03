## Context

`content.manifest.json` 已有 `section` 字段，但集合页忽略它，`DocNav` 只按 collection 计算相邻文档。Deep Agents 导入器当前按文件路径排序，主题名称由目录名机械转换，缺少学习顺序和总览文档优先级。

## Goals / Non-Goals

**Goals:**

- 保留一个 Deep Agents collection，同时提供清晰的主题层级。
- 使用固定主题顺序和中文/英文友好标签。
- 让集合页和文档导航都遵循主题边界。
- 保持现有文档 ID、URL 和其他 collection 行为不变。

**Non-Goals:**

- 不拆成 11 个 collection。
- 不新增嵌套路由或数据库。
- 不改写文档正文和源码资源。

## Decisions

### 主题元数据由导入器维护

增加 Deep Agents topic 配置，声明目录名、显示名、顺序。导入时将 `section` 写成显示名，并按 topic order、总览文档优先、文件名排序。总览文档通过无数字前缀或 `README/overview/backends` 等主题索引名识别。

### 集合页按 section 分组

集合页仅对 `deep-agents` 分组，其他 collection 保持当前平铺布局。分组顺序取文档排序后的首次出现顺序，避免额外 schema 字段；每组显示标题、数量和卡片网格。

### 导航限制在当前 section

文档详情页计算 Deep Agents 的 prev/next 时，同时过滤 collection 和 section；其他 collection 仍按 collection 全量导航。这样不会破坏 LangGraph 的基础篇/编排篇/工程篇连续学习路径。

## Risks / Trade-offs

- [主题总览文档命名不统一] → 使用明确的文件名规则和稳定排序兜底，未知文件仍按字典序排列。
- [主题分组增加页面长度] → 每组保留紧凑双列卡片；移动端自动单列。
- [未来新增主题未配置] → 导入器将未知目录追加到末尾，并使用目录格式化名称，不阻塞导入。

## Migration Plan

1. 更新导入器并重新生成 manifest/content。
2. 更新 collection 页和文档导航。
3. 运行测试、资源检查和构建，确认旧 URL 与非 Deep Agents collection 无回归。
