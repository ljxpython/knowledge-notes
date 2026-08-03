## Why

Deep Agents 当前作为一个 collection 展示，但其 11 个教学子目录被压成一张 97 篇文章的平铺列表。用户无法快速看出 Skills、Memory、Backend、Frontend 等主题边界，文档上一篇/下一篇还会跨主题跳转。

## What Changes

- 将 Deep Agents 子目录映射为有顺序的主题分组，并显示主题名称与文章数量。
- 集合页按主题分组渲染文档卡片，主题总览文档排在各组前面。
- Deep Agents 文档的上一篇/下一篇只在当前主题内导航。
- 保持 `deep-agents` collection 和现有文档 URL 不变。

## Capabilities

### New Capabilities

- `deep-agents-topic-navigation`: 在 Deep Agents collection 中按子目录组织内容并提供主题内导航。

### Modified Capabilities

无。

## Impact

- 修改 Deep Agents 导入排序和主题元数据。
- 修改 collection 页面分组渲染和文档导航计算。
- 扩展页面测试/构建验证；不新增依赖，不改变其他 collection 的布局和导航语义。
