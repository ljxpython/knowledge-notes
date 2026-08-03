import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { execFileSync } from 'node:child_process';
import { basename, dirname, extname, relative, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const outputDir = resolve(root, 'content');
const examplesDir = resolve(root, 'public/examples');
const siteBase = '/knowledge-notes';
const sourceRepo = 'https://github.com/ljxpython/open_deep_research';
const deepAgentsRepo = 'https://github.com/ljxpython/langgraph_teach';
const allowedCodeExtensions = new Set(['.py', '.ts', '.tsx', '.js', '.mjs']);
const ignoredPathParts = new Set(['node_modules', '__pycache__', 'workspace', '.logs']);
const deepAgentTopics = [
  ['skills_teach', 'Skills', '技能加载、发现、资源和权限。'],
  ['memory_teach', 'Memory / 记忆', 'Agent memory 的加载、隔离、权限和生产设计。'],
  ['context_engineering_teach', 'Context Engineering', '输入上下文、运行时上下文、压缩和隔离。'],
  ['backend_teach', 'Backends / 后端', 'State、Filesystem、Store、Composite 和权限边界。'],
  ['subagents_teach', 'Subagents / 子 Agent', '子 Agent 的上下文、并发、结构化输出和禁用策略。'],
  ['human_loop_teach', 'Human-in-the-loop / 人机回路', '审批、中断、恢复和文件权限确认。'],
  ['frontend_teach', 'Frontend / 前端', 'useStream、工具事件、文件、分支和生成式 UI。'],
  ['profiles_teach', 'Profiles / 模型配置', 'Harness profile、工具可见性和模型能力差异。'],
  ['advanced_teach', 'Advanced / 高级能力', 'Interpreter、sandbox、事件流、容错和生产评估。'],
  ['middleware_teach', 'Middleware / 中间件', '模型和工具生命周期钩子、默认栈与状态扩展。'],
  ['a2a_teach', 'A2A / 远程 Agent', 'Agent-to-Agent 服务、流式、认证和远程编排。'],
];
const deepAgentTopicMeta = new Map(deepAgentTopics.map(([id, label, description], order) => [id, { label, description, order }]));

const legacyLangGraphMeta = {
  '01-real-model-agent': ['第 1 章：真实模型与消息', 'init_chat_model、消息对象与一次真实 ainvoke 调用。', '基础篇'],
  '02-state-and-command': ['第 2 章：状态与动态路由', 'MessagesState、reducer、StateGraph 与 Command 路由。', '基础篇'],
  '03-structured-output': ['第 3 章：结构化输出', 'Pydantic schema 与 with_structured_output 的可控决策。', '基础篇'],
  '04-tool-loop': ['第 4 章：工具循环', '工具绑定、ToolMessage 与真实 ReAct 闭环。', '基础篇'],
  '05-search-and-mcp': ['第 5 章：搜索与 MCP', '搜索工具、MCP 装配与外部工具边界。', '基础篇'],
  '06-subgraphs-and-concurrency': ['第 6 章：子图与并发', 'supervisor/researcher 子图、asyncio.gather 与汇总。', '编排篇'],
  '07-persistence-streaming-observability': ['第 7 章：持久化、流式与观测', 'checkpointer、thread_id、LangSmith 与事件流。', '编排篇'],
  '08-integrated-mini-researcher': ['第 8 章：综合迷你研究员', '把前七章知识点串成离线 mini researcher。', '编排篇'],
  '09-coverage-matrix': ['第 9 章：项目知识覆盖矩阵', '将概念、项目源码和真实示例映射为学习矩阵。', '工程篇'],
  '10-end-to-end-workflow': ['第 10 章：从用户问题到最终报告的完整链路', '追踪澄清、简报、并发研究和报告生成的数据流。', '工程篇'],
  '11-configuration-security-and-runtime': ['第 11 章：配置、密钥、身份与运行时边界', 'RunnableConfig、密钥来源、MCP 和 owner 授权边界。', '工程篇'],
  '12-resilience-testing-and-migration': ['第 12 章：容错、测试、评估与升级判断', '重试、上下文限制、并发异常和 API 升级策略。', '工程篇'],
  '13-code-reading-exercises': ['第 13 章：源码阅读练习', '围绕 reducer、工具协议、配置和异常路径的练习。', '工程篇'],
};

const sourceDefaults = {
  langgraph: {
    id: 'langgraph',
    collection: 'langgraph-langchain',
    title: 'LangGraph / LangChain 工程实践',
    description: '基于 Open Deep Research 主实现，系统学习 LangGraph 与 LangChain 的工程用法。',
    order: 1,
    sourceRepo,
    remotePath: 'docs/langgraph-learning',
    sourceLabel: '查看源文档',
    notice: '本站只展示学习文档。文中的 Python、模型、搜索和 MCP 命令均不会在构建或部署时执行；手动运行可能需要密钥并产生费用。',
  },
  langchain: {
    id: 'langchain',
    collection: 'langchain-v1',
    title: 'LangChain v1 Agent 学习路线',
    description: '围绕 LangChain v1 的 create_agent、消息、工具、记忆、中间件和子 Agent 学习。',
    order: 2,
    sourceRepo,
    remotePath: 'docs/langchain',
    sourceLabel: '查看源文档',
    notice: '本站只展示学习文档。示例不会在构建或部署时执行；手动运行可能需要 API Key 并产生模型费用。',
  },
  deepAgents: {
    id: 'deep-agents',
    collection: 'deep-agents',
    title: 'Deep Agents 工程教学',
    description: '从 skills、memory、backend、middleware 到多 Agent、HITL、前端和 A2A 的 Deep Agents 实践。',
    order: 3,
    sourceRepo: deepAgentsRepo,
    remotePath: 'deepagent_src',
    sourceLabel: '查看源文档',
    notice: '本站只展示教学文档和静态源码。不会执行示例、启动服务、访问模型、数据库或其他外部系统。',
  },
};

function slugify(value) {
  return value
    .normalize('NFKC')
    .replace(/\.[^.]+$/, '')
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase();
}

function walkFiles(dir) {
  if (!existsSync(dir)) return [];
  const files = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const file = resolve(dir, entry.name);
    if (entry.isDirectory()) files.push(...walkFiles(file));
    else files.push(file);
  }
  return files;
}

function findGitRoot(startDir) {
  let current = resolve(startDir);
  while (current !== dirname(current)) {
    if (existsSync(resolve(current, '.git'))) return current;
    current = dirname(current);
  }
  return null;
}

export function trackedFiles(sourceDir) {
  const gitRoot = findGitRoot(sourceDir);
  if (!gitRoot) throw new Error(`Deep Agents source is not inside a Git repository: ${sourceDir}`);
  const prefix = relative(gitRoot, sourceDir).split(sep).join('/');
  const output = execFileSync('git', ['-C', gitRoot, 'ls-files', `${prefix}/`], { encoding: 'utf8' });
  return output.split(/\r?\n/).filter(Boolean).map((file) => resolve(gitRoot, file));
}

function isIgnored(file, sourceDir) {
  return relative(sourceDir, file).split(sep).some((part) => ignoredPathParts.has(part));
}

function firstHeading(markdown, fallback) {
  const heading = markdown.match(/^#\s+(.+)$/m);
  return heading ? heading[1].trim() : fallback;
}

function descriptionFrom(markdown, title) {
  const body = markdown
    .replace(/^#\s+.+\r?\n*/, '')
    .split(/\r?\n\s*\r?\n/)
    .map((part) => part.replace(/[`*_>#-]/g, '').trim())
    .find(Boolean);
  return body ? body.slice(0, 160) : `${title} 教学文档。`;
}

function splitFragment(target) {
  const index = target.indexOf('#');
  return index === -1 ? [target, ''] : [target.slice(0, index), target.slice(index)];
}

function parseLinkTarget(inner) {
  const value = inner.trim();
  if (value.startsWith('<')) {
    const end = value.indexOf('>');
    if (end !== -1) return [value.slice(1, end), value.slice(end + 1)];
  }
  const title = value.match(/^(\S+)(\s+["'][^"']*["'])$/);
  return title ? [title[1], title[2]] : [value, ''];
}

function relativeKey(file) {
  return resolve(file).split(sep).join('/');
}

function sourceUrl(config, file, suffix = 'blob') {
  const path = relative(config.repoRoot, file).split(sep).join('/');
  return `${config.sourceRepo}/${suffix}/main/${path}`;
}

function localExampleUrl(file, context) {
  const config = context.configs.find((item) => file.startsWith(`${item.sourceDir}${sep}`));
  if (!config) throw new Error(`Example file is outside configured sources: ${file}`);
  const relativePath = relative(config.sourceDir, file).split(sep).join('/');
  return `${siteBase}/examples/${config.collection}/${relativePath}`;
}

function oldLangGraphLink(target) {
  const [path, fragment] = splitFragment(target);
  const id = path.replace(/\.md$/, '');
  if (legacyLangGraphMeta[id]) return `${siteBase}/docs/langgraph-langchain/${id}/${fragment}`;
  return null;
}

function buildContext(entries, codeFiles, configs) {
  const docsByFile = new Map(entries.map((entry) => [relativeKey(entry.sourceFile), entry]));
  const codeByFile = new Map(codeFiles.map((file) => [relativeKey(file), file]));
  const docsByBasename = new Map();
  for (const entry of entries) {
    const key = slugify(entry.id.split('-').slice(-1)[0]);
    if (!docsByBasename.has(key)) docsByBasename.set(key, []);
    docsByBasename.get(key).push(entry);
  }
  return { entries, docsByFile, codeByFile, docsByBasename, configs };
}

function registerResource(entry, file, context) {
  if (!file || !allowedCodeExtensions.has(extname(file).toLowerCase())) return;
  const url = localExampleUrl(file, { ...context, collection: entry.collection });
  if (!entry.resources.some((resource) => resource.url === url)) {
    entry.resources.push({ label: `查看示例代码：${relative(entry.repoRoot, file).split(sep).join('/')}`, url });
  }
}

function resolveTarget(target, sourceFile, context, entry) {
  if (/^(?:https?:|mailto:|#)/.test(target)) return target;
  if (target.startsWith('/langgraph-langchain-learning-site/docs/')) {
    return target.replace('/langgraph-langchain-learning-site/docs/', `${siteBase}/docs/langgraph-langchain/`);
  }

  const [path, fragment] = splitFragment(target);
  const legacy = oldLangGraphLink(target);
  if (legacy) return legacy;
  const candidate = resolve(dirname(sourceFile), path);
  const doc = context.docsByFile.get(relativeKey(candidate));
  if (doc) return `${siteBase}/docs/${doc.collection}/${doc.id}/${fragment}`;

  const code = context.codeByFile.get(relativeKey(candidate));
  if (code) {
    registerResource(entry, code, context);
    return `${localExampleUrl(code, { ...context, collection: entry.collection })}${fragment}`;
  }

  if (path === '../README.md' || path === '../../README.md' || path.endsWith('/README.md')) {
    const config = context.configs.find((item) => candidate.startsWith(`${item.sourceDir}${sep}`));
    if (config) return `${siteBase}/collections/${config.collection}/`;
  }

  const config = context.configs.find((item) => sourceFile.startsWith(`${item.sourceDir}${sep}`));
  if (config && config.repoRoot && candidate.startsWith(`${config.repoRoot}${sep}`)) {
    return `${config.sourceRepo}/blob/main/${relative(config.repoRoot, candidate).split(sep).join('/')}${fragment}`;
  }

  throw new Error(`${sourceFile}: unsupported relative link "${target}"`);
}

export function rewriteMarkdown(markdown, sourceFile, context, entry) {
  return markdown.replace(/(\[[^\]]*\])\(([^)]+)\)/g, (match, label, inner) => {
    const [target, title] = parseLinkTarget(inner);
    const rewritten = context ? resolveTarget(target, sourceFile, context, entry) : oldLangGraphLink(target);
    if (!rewritten) throw new Error(`${sourceFile}: unsupported relative link "${target}"`);
    return `${label}(${rewritten}${title})`;
  });
}

export function rewriteLink(target, sourceFile, context) {
  if (context) return resolveTarget(target, sourceFile, context, { resources: [], collection: 'langgraph-langchain', repoRoot: dirname(sourceFile) });
  if (/^(?:https?:|mailto:|#)/.test(target)) return target;
  if (target.startsWith('/langgraph-langchain-learning-site/docs/')) {
    return target.replace('/langgraph-langchain-learning-site/docs/', `${siteBase}/docs/langgraph-langchain/`);
  }
  const legacy = oldLangGraphLink(target);
  if (legacy) return legacy;
  if (/^examples\/[^/]+\.py$/.test(target)) {
    return `${sourceRepo}/blob/main/docs/langgraph-learning/${target}`;
  }
  if (target.startsWith('../../src/')) return `${sourceRepo}/blob/main/${target.slice('../../'.length)}`;
  throw new Error(`${sourceFile}: unsupported relative link "${target}"`);
}

function createConfig(kind, sourceDir) {
  const base = sourceDefaults[kind];
  if (!sourceDir) throw new Error(`Missing source directory for ${kind}.`);
  const resolvedDir = resolve(sourceDir);
  if (!existsSync(resolvedDir)) throw new Error(`Missing source directory: ${resolvedDir}`);
  const repoRoot = findGitRoot(resolvedDir) ?? resolve(resolvedDir, '..');
  return { ...base, sourceDir: resolvedDir, repoRoot };
}

function collectSourceFiles(config) {
  if (config.id === 'deep-agents') {
    const tracked = trackedFiles(config.sourceDir).filter((file) => !isIgnored(file, config.sourceDir));
    return {
      docs: tracked.filter((file) => file.endsWith('.md') && file.includes(`${sep}docs${sep}`)),
      code: tracked.filter((file) => allowedCodeExtensions.has(extname(file).toLowerCase())),
    };
  }
  const files = walkFiles(config.sourceDir);
  return {
    docs: files.filter((file) => file.endsWith('.md') && file.split(sep).at(-1) !== 'README.md'),
    code: files.filter((file) => allowedCodeExtensions.has(extname(file).toLowerCase())),
  };
}

function topicFor(config, file) {
  if (config.id !== 'deep-agents') return '';
  const rel = relative(config.sourceDir, file).split(sep);
  return rel[0] ?? 'root';
}

function topicMeta(topic) {
  return deepAgentTopicMeta.get(topic) ?? {
    label: topic.replace(/[_-]+/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase()),
    description: 'Deep Agents 教学主题。',
    order: deepAgentTopics.length,
  };
}

function isOverviewDocument(file) {
  const name = basename(file).toLowerCase();
  if (/^\d+[_ -]/.test(name)) return name.startsWith('00');
  return true;
}

export function documentId(config, file) {
  const base = slugify(basename(file));
  if (config.id === 'langgraph') return base;
  if (config.id === 'langchain') return `langchain-v1-${base}`;
  return `deep-agents-${slugify(topicFor(config, file))}-${base}`;
}

export function assertUniqueDocumentIds(entries) {
  const seen = new Set();
  for (const entry of entries) {
    if (seen.has(entry.id)) throw new Error(`Duplicate document ID "${entry.id}"`);
    seen.add(entry.id);
  }
}

function sectionFor(config, file) {
  if (config.id !== 'deep-agents') return config.id === 'langgraph' ? (legacyLangGraphMeta[slugify(relative(config.sourceDir, file))]?.[2] ?? 'LangGraph') : 'LangChain v1';
  return topicMeta(topicFor(config, file)).label;
}

function sourcePath(config, file) {
  if (config.id === 'deep-agents') return relative(config.repoRoot, file).split(sep).join('/');
  return `${config.remotePath}/${relative(config.sourceDir, file).split(sep).join('/')}`;
}

function companionCodeFiles(config, docFile, codeFiles) {
  const docBase = slugify(docFile.split(sep).at(-1));
  return codeFiles.filter((file) => {
    const codeBase = slugify(file.split(sep).at(-1));
    return codeBase === docBase || (file.startsWith(`${dirname(docFile)}${sep.replaceAll('/', sep)}`) && codeBase.startsWith(docBase));
  });
}

export function importCourse({ langgraphDir, langchainDir, deepAgentsDir, outputDirectory = outputDir, examplesDirectory = examplesDir, manifestOutputPath = resolve(root, 'content.manifest.json') } = {}) {
  const configs = [
    createConfig('langgraph', langgraphDir ?? process.env.OPEN_DEEP_RESEARCH_LANGGRAPH),
    createConfig('langchain', langchainDir ?? process.env.OPEN_DEEP_RESEARCH_LANGCHAIN),
    createConfig('deepAgents', deepAgentsDir ?? process.env.DEEPAGENT_SRC),
  ];
  const files = configs.map((config) => ({ config, ...collectSourceFiles(config) }));
  const codeFiles = files.flatMap(({ code }) => code);
  const entries = [];
  for (const { config, docs } of files) {
    docs.sort((a, b) => {
      if (config.id !== 'deep-agents') return relative(config.sourceDir, a).localeCompare(relative(config.sourceDir, b));
      const topicA = topicMeta(topicFor(config, a));
      const topicB = topicMeta(topicFor(config, b));
      return topicA.order - topicB.order
        || Number(!isOverviewDocument(a)) - Number(!isOverviewDocument(b))
        || relative(config.sourceDir, a).localeCompare(relative(config.sourceDir, b));
    });
    docs.forEach((sourceFile, index) => {
      const id = documentId(config, sourceFile);
      const markdown = readFileSync(sourceFile, 'utf8');
      const legacy = config.id === 'langgraph' ? legacyLangGraphMeta[id] : null;
      const title = legacy?.[0] ?? firstHeading(markdown, id);
      entries.push({
        id,
        collection: config.collection,
        title,
        description: legacy?.[1] ?? descriptionFrom(markdown, title),
        section: legacy?.[2] ?? sectionFor(config, sourceFile),
        order: config.id === 'langgraph' ? index + 1 : index + 1,
        published: true,
        source: `${config.sourceRepo}/blob/main/${sourcePath(config, sourceFile)}`,
        sourceFile,
        sourceDir: config.sourceDir,
        repoRoot: config.repoRoot,
        resources: [],
        config,
      });
    });
  }
  assertUniqueDocumentIds(entries);

  const context = buildContext(entries, codeFiles, configs);
  const outputCollections = configs.map(({ sourceDir, ...config }) => ({
    id: config.collection,
    title: config.title,
    description: config.description,
    order: config.order,
    sourceLabel: config.sourceLabel,
    sourceUrl: `${config.sourceRepo}/tree/main/${config.remotePath}`,
    notice: config.notice,
  }));

  rmSync(outputDirectory, { recursive: true, force: true });
  mkdirSync(outputDirectory, { recursive: true });
  for (const config of configs) rmSync(resolve(examplesDirectory, config.collection), { recursive: true, force: true });

  for (const file of codeFiles) {
    const config = configs.find((item) => file.startsWith(`${item.sourceDir}${sep}`));
    if (!config) continue;
    const relativePath = relative(config.sourceDir, file).split(sep).join('/');
    const destination = resolve(examplesDirectory, config.collection, relativePath);
    mkdirSync(dirname(destination), { recursive: true });
    copyFileSync(file, destination);
  }

  const documents = {};
  for (const entry of entries) {
    const markdown = readFileSync(entry.sourceFile, 'utf8');
    const companion = companionCodeFiles(entry.config, entry.sourceFile, codeFiles);
    companion.forEach((file) => registerResource(entry, file, context));
    const rewritten = rewriteMarkdown(markdown, entry.sourceFile, context, entry);
    writeFileSync(resolve(outputDirectory, `${entry.id}.md`), rewritten, 'utf8');
    documents[entry.id] = {
      collection: entry.collection,
      title: entry.title,
      description: entry.description,
      section: entry.section,
      order: entry.order,
      published: entry.published,
      source: entry.source,
      resources: entry.resources,
    };
  }

  writeFileSync(manifestOutputPath, `${JSON.stringify({ collections: outputCollections, documents }, null, 2)}\n`, 'utf8');
  console.log(`Imported ${entries.length} documents and ${codeFiles.length} example files.`);
}

function cliOptions(args) {
  if (args.length === 3) return { langgraphDir: args[0], langchainDir: args[1], deepAgentsDir: args[2] };
  if (args.length !== 0) throw new Error('Pass exactly three source directories: <langgraph-learning> <langchain> <deepagent_src>.');
  return {};
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  importCourse(cliOptions(process.argv.slice(2)));
}
