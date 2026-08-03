## ADDED Requirements

### Requirement: 多来源文档导入
系统 MUST 支持从三个显式来源目录导入 Markdown：Open Deep Research 的 `docs/langgraph-learning`、`docs/langchain`，以及 `langgraph_teach/deepagent_src` 下 Git 跟踪的教学文档。

#### Scenario: 导入三个来源
- **WHEN** 使用三个有效源目录运行内容导入命令
- **THEN** 系统生成三个对应 collection 的文档内容和 manifest 元数据

#### Scenario: 缺少必需源目录
- **WHEN** 任一显式源目录不存在或不可读
- **THEN** 导入命令失败并指出具体源目录，不生成不完整的 manifest

### Requirement: 稳定且唯一的文档标识
系统 MUST 为生成文档分配全局唯一的 ID，并 MUST 保持现有 LangGraph 13 篇文档 ID 和 URL 不变。

#### Scenario: Deep Agents 同名文档
- **WHEN** 不同 Deep Agents 主题包含相同文件名
- **THEN** 系统使用主题命名空间生成不同 ID、文件名和路由

#### Scenario: 旧文档路由回归
- **WHEN** 构建完成后访问现有 13 篇 LangGraph 文档路径
- **THEN** 每个路径仍生成页面并显示原文档内容

### Requirement: 相对链接重写
系统 MUST 按源文件目录解析并重写文档之间的相对链接、示例代码链接、项目源码链接和锚点；无法解析的相对链接 MUST 使导入失败。

#### Scenario: 文档链接映射到站内页面
- **WHEN** Markdown 链接指向同一来源的另一个文档
- **THEN** 链接目标是对应 collection 下的站内文档 URL，并保留 fragment

#### Scenario: 外部链接保持原样
- **WHEN** Markdown 链接是 HTTP、HTTPS、mailto 或纯锚点
- **THEN** 系统不改写其目标

#### Scenario: 未支持的相对链接
- **WHEN** 相对链接无法映射到已导入文档或源码资源
- **THEN** 导入失败并报告源文件路径和原始链接

### Requirement: 教学示例源码可见
系统 MUST 将允许范围内的教学示例源码复制为站内静态资源，并在对应文档 metadata 中提供可访问链接。

#### Scenario: Python 示例可访问
- **WHEN** 文档声明一个存在的 Python 示例
- **THEN** 构建输出包含对应 `public/examples` 资源，文档页面显示可打开的示例源码链接

#### Scenario: 前端教学源码可访问
- **WHEN** Git 跟踪的教学文档引用 `.ts`、`.tsx`、`.js` 或 `.mjs` 示例
- **THEN** 系统按同样规则复制资源并生成链接

#### Scenario: 缺少示例资源
- **WHEN** manifest 声明的示例文件不存在
- **THEN** 内容校验失败并指出文档和资源路径

### Requirement: 导入边界与安全
系统 MUST 只导入允许的文档和源码扩展名，MUST 排除依赖、缓存、workspace、日志、数据库和生成目录，并 MUST 不执行任何导入内容中的命令。

#### Scenario: 工作目录包含依赖和运行产物
- **WHEN** Deep Agents 源目录包含 `node_modules`、`__pycache__`、workspace 或日志文件
- **THEN** 这些文件不会出现在生成内容或 public 示例资源中

#### Scenario: 构建静态站
- **WHEN** 运行导入、测试或 Astro build
- **THEN** 系统只读取和复制文件，不执行 Python、模型、搜索、MCP、数据库或前端服务代码

### Requirement: 可重复验证
系统 MUST 提供覆盖三类来源、ID 冲突、链接重写、示例存在性和构建结果的自动化验证。

#### Scenario: 内容导入测试
- **WHEN** 运行项目测试命令
- **THEN** 测试验证合法导入成功、缺失源失败、重复 ID 失败和坏相对链接失败

#### Scenario: 生产构建检查
- **WHEN** 运行 `npm run assets:check` 和 `npm run build`
- **THEN** 所有 manifest 文档和源码资源存在，Astro 构建成功且没有未解析内容链接
