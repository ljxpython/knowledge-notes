export interface CollectionConfig {
  id: string;
  title: string;
  description: string;
  order: number;
  sectionMode?: 'flat' | 'collapsible';
  notice?: string;
  sourceLabel?: string;
  sourceUrl?: string;
}

export const site = {
  title: 'Knowledge Notes',
  description: '面向多个技术主题的知识笔记展示站，用统一模板组织学习文档、源码阅读和实践路线。',
  author: 'ljxpython',
  url: 'https://ljxpython.github.io',
  base: '/knowledge-notes',
  repositoryUrl: 'https://github.com/ljxpython/knowledge-notes',
  accent: {
    primary: '#a56a15',
    soft: '#f4e8d3',
  },
  navigation: {
    label: 'Knowledge Notes',
    sourceLabel: '查看源文档',
  },
  links: {
    github: 'https://github.com/ljxpython/knowledge-notes',
  },
  collections: [
    {
      id: 'langgraph-langchain',
      title: 'LangGraph / LangChain 工程实践',
      description: '基于 Open Deep Research 主实现，系统学习 LangGraph 与 LangChain 的工程用法。',
      order: 1,
      sectionMode: 'collapsible' as const,
      sourceLabel: '查看源文档',
      sourceUrl: 'https://github.com/ljxpython/open_deep_research/tree/main/docs/langgraph-learning',
      notice: '本站只展示学习文档。文中的 Python、模型、搜索和 MCP 命令均不会在构建或部署时执行；手动运行可能需要密钥并产生费用。',
    },
    {
      id: 'langchain-v1',
      title: 'LangChain v1 Agent 学习路线',
      description: '围绕 LangChain v1 的 create_agent、消息、工具、记忆、中间件和子 Agent 学习。',
      order: 2,
      sectionMode: 'flat' as const,
      sourceLabel: '查看源文档',
      sourceUrl: 'https://github.com/ljxpython/open_deep_research/tree/main/docs/langchain',
      notice: '本站只展示学习文档。示例不会在构建或部署时执行；手动运行可能需要 API Key 并产生模型费用。',
    },
    {
      id: 'deep-agents',
      title: 'Deep Agents 工程教学',
      description: '从 skills、memory、backend、middleware 到多 Agent、HITL、前端和 A2A 的 Deep Agents 实践。',
      order: 3,
      sectionMode: 'collapsible' as const,
      sourceLabel: '查看源文档',
      sourceUrl: 'https://github.com/ljxpython/langgraph_teach/tree/main/deepagent_src',
      notice: '本站只展示教学文档和静态源码。不会执行示例、启动服务、访问模型、数据库或其他外部系统。',
    },
  ],
} as const;

export default site;
