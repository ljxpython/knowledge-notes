## ADDED Requirements

### Requirement: Deep Agents 主题分组
Deep Agents collection MUST 按教学子目录分组展示文档，每组 MUST 显示主题名称和文档数量。

#### Scenario: 集合页展示主题组
- **WHEN** 用户打开 Deep Agents collection 页面
- **THEN** 页面按主题显示多个分组，而不是把所有文档放在一个列表中

#### Scenario: 未知主题目录
- **WHEN** 导入源出现未配置的新主题目录
- **THEN** 文档被放入末尾的格式化主题组，导入不会失败

### Requirement: 稳定主题顺序
系统 MUST 按配置的学习顺序排列已知主题，并 MUST 将主题总览文档排在该主题的章节文档之前。

#### Scenario: 主题顺序
- **WHEN** 导入 Deep Agents 文档
- **THEN** Skills、Memory、Context Engineering 等主题按配置顺序出现，不能按字母顺序打乱

#### Scenario: 主题内文档顺序
- **WHEN** 一个主题同时包含总览文档和编号章节
- **THEN** 总览文档首先出现，其余章节按编号/文件名稳定排序

### Requirement: 主题内文档导航
Deep Agents 文档的上一篇/下一篇 MUST 只指向同一主题内的文档；其他 collection 的导航行为 MUST 保持不变。

#### Scenario: Deep Agents 主题边界
- **WHEN** 用户浏览某主题的第一篇或最后一篇文章
- **THEN** 对应方向没有跳转到另一个 Deep Agents 主题

#### Scenario: 其他 collection 回归
- **WHEN** 用户浏览 LangGraph 或 LangChain v1 文档
- **THEN** 导航仍按原 collection 顺序工作
