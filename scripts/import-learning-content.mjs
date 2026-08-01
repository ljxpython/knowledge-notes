import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const outputDir = resolve(root, 'content');
const defaultSourceDir = '/Users/lijiaxin/PyCharmMiscProject/research/open_deep_research/docs/langgraph-langchain-learning';
const sourceRepo = 'https://github.com/ljxpython/open_deep_research';
const siteBase = '/knowledge-notes';
const collectionId = 'langgraph-langchain';

const collections = [
  {
    id: collectionId,
    title: 'LangGraph / LangChain 工程实践',
    description: '基于 Open Deep Research 主实现，系统学习 LangGraph 与 LangChain 的工程用法。',
    order: 1,
    sourceLabel: '查看源文档',
    sourceUrl: `${sourceRepo}/tree/main/docs/langgraph-langchain-learning`,
    notice: '本站只展示学习文档。文中的 Python、模型、搜索和 MCP 命令均不会在构建或部署时执行；手动运行可能需要密钥并产生费用。',
  },
];

const chapters = [
  ['01-real-model-agent', '第 1 章：真实模型与消息', 'init_chat_model、消息对象与一次真实 ainvoke 调用。', '基础篇'],
  ['02-state-and-command', '第 2 章：状态与动态路由', 'MessagesState、reducer、StateGraph 与 Command 路由。', '基础篇'],
  ['03-structured-output', '第 3 章：结构化输出', 'Pydantic schema 与 with_structured_output 的可控决策。', '基础篇'],
  ['04-tool-loop', '第 4 章：工具循环', '工具绑定、ToolMessage 与真实 ReAct 闭环。', '基础篇'],
  ['05-search-and-mcp', '第 5 章：搜索与 MCP', '搜索工具、MCP 装配与外部工具边界。', '基础篇'],
  ['06-subgraphs-and-concurrency', '第 6 章：子图与并发', 'supervisor/researcher 子图、asyncio.gather 与汇总。', '编排篇'],
  ['07-persistence-streaming-observability', '第 7 章：持久化、流式与观测', 'checkpointer、thread_id、LangSmith 与事件流。', '编排篇'],
  ['08-integrated-mini-researcher', '第 8 章：综合迷你研究员', '把前七章知识点串成离线 mini researcher。', '编排篇'],
  ['09-coverage-matrix', '第 9 章：项目知识覆盖矩阵', '将概念、项目源码和真实示例映射为学习矩阵。', '工程篇'],
  ['10-end-to-end-workflow', '第 10 章：从用户问题到最终报告的完整链路', '追踪澄清、简报、并发研究和报告生成的数据流。', '工程篇'],
  ['11-configuration-security-and-runtime', '第 11 章：配置、密钥、身份与运行时边界', 'RunnableConfig、密钥来源、MCP 和 owner 授权边界。', '工程篇'],
  ['12-resilience-testing-and-migration', '第 12 章：容错、测试、评估与升级判断', '重试、上下文限制、并发异常和 API 升级策略。', '工程篇'],
  ['13-code-reading-exercises', '第 13 章：源码阅读练习', '围绕 reducer、工具协议、配置和异常路径的练习。', '工程篇'],
];

const chapterPaths = new Map(chapters.map(([id]) => [`${id}.md`, id]));

function splitFragment(target) {
  const index = target.indexOf('#');
  return index === -1 ? [target, ''] : [target.slice(0, index), target.slice(index)];
}

export function rewriteLink(target, sourceFile) {
  if (/^(?:https?:|mailto:|#)/.test(target)) return target;
  if (target.startsWith('/langgraph-langchain-learning-site/docs/')) {
    return target.replace('/langgraph-langchain-learning-site/docs/', `${siteBase}/docs/${collectionId}/`);
  }

  const [path, fragment] = splitFragment(target);
  const chapter = chapterPaths.get(path);
  if (chapter) return `${siteBase}/docs/${collectionId}/${chapter}/${fragment}`;

  if (/^examples\/[^/]+\.py$/.test(path)) {
    return `${sourceRepo}/blob/main/docs/langgraph-langchain-learning/${path}${fragment}`;
  }

  if (path.startsWith('../../src/')) {
    return `${sourceRepo}/blob/main/${path.slice('../../'.length)}${fragment}`;
  }

  throw new Error(`${sourceFile}: unsupported relative link "${target}"`);
}

export function rewriteMarkdown(markdown, sourceFile) {
  return markdown.replace(/\[([^\]]+)\]\(([^)\s]+)(\s+["'][^)]*["'])?\)/g, (match, label, target, title = '') => {
    return `[${label}](${rewriteLink(target, sourceFile)}${title})`;
  });
}

export function importCourse(sourceDir = process.env.OPEN_DEEP_RESEARCH_DOCS || defaultSourceDir) {
  for (const [id] of chapters) {
    const file = resolve(sourceDir, `${id}.md`);
    if (!existsSync(file)) throw new Error(`Missing course chapter: ${file}`);
  }

  mkdirSync(outputDir, { recursive: true });
  for (const file of readdirSync(outputDir).filter((name) => name.endsWith('.md'))) {
    rmSync(resolve(outputDir, file));
  }

  const documents = {};
  chapters.forEach(([id, title, description, section], index) => {
    const sourceFile = resolve(sourceDir, `${id}.md`);
    const markdown = readFileSync(sourceFile, 'utf8');
    writeFileSync(resolve(outputDir, `${id}.md`), rewriteMarkdown(markdown, sourceFile), 'utf8');
    documents[id] = {
      collection: collectionId,
      title,
      description,
      section,
      order: index + 1,
      published: true,
      source: `${sourceRepo}/blob/main/docs/langgraph-langchain-learning/${id}.md`,
    };
  });

  writeFileSync(resolve(root, 'content.manifest.json'), `${JSON.stringify({ collections, documents }, null, 2)}\n`, 'utf8');
  console.log(`Imported ${chapters.length} learning chapters from ${sourceDir}.`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  importCourse();
}
