import assert from 'node:assert/strict';
import test from 'node:test';
import { resolve } from 'node:path';
import { assertUniqueDocumentIds, documentId, importCourse, rewriteLink, rewriteMarkdown } from './import-learning-content.mjs';

const sourceDir = resolve('/tmp/knowledge-notes-source');
const sourceFile = resolve(sourceDir, 'chapter.md');
const nextFile = resolve(sourceDir, 'next.md');
const exampleFile = resolve(sourceDir, 'examples/demo.py');

function context() {
  return {
    configs: [{ sourceDir, repoRoot: resolve('/tmp'), collection: 'langchain-v1', sourceRepo: 'https://example.com/repo' }],
    docsByFile: new Map([[nextFile, { collection: 'langchain-v1', id: 'langchain-v1-next' }]]),
    codeByFile: new Map([[exampleFile, exampleFile]]),
  };
}

test('rewrites legacy chapter links to preserved site routes', () => {
  assert.equal(
    rewriteLink('03-structured-output.md', 'test.md'),
    '/knowledge-notes/docs/langgraph-langchain/03-structured-output/',
  );
  assert.equal(
    rewriteLink('/langgraph-langchain-learning-site/docs/03-structured-output/', 'test.md'),
    '/knowledge-notes/docs/langgraph-langchain/03-structured-output/',
  );
});

test('rewrites upstream examples and source links to current paths', () => {
  assert.equal(
    rewriteLink('examples/01_real_model_agent.py', 'test.md'),
    'https://github.com/ljxpython/open_deep_research/blob/main/docs/langgraph-learning/examples/01_real_model_agent.py',
  );
  assert.equal(
    rewriteLink('../../src/open_deep_research/state.py', 'test.md'),
    'https://github.com/ljxpython/open_deep_research/blob/main/src/open_deep_research/state.py',
  );
});

test('resolves documents, fragments, and local example resources', () => {
  const entry = { collection: 'langchain-v1', repoRoot: resolve('/tmp'), resources: [] };
  assert.equal(
    rewriteLink('next.md#details', sourceFile, context()),
    '/knowledge-notes/docs/langchain-v1/langchain-v1-next/#details',
  );
  assert.equal(
    rewriteLink('examples/demo.py', sourceFile, { ...context(), collection: 'langchain-v1' }),
    '/knowledge-notes/examples/langchain-v1/examples/demo.py',
  );
  const markdown = rewriteMarkdown('[demo](examples/demo.py "source")', sourceFile, context(), entry);
  assert.equal(markdown, '[demo](/knowledge-notes/examples/langchain-v1/examples/demo.py "source")');
});

test('namespaces repeated Deep Agents filenames', () => {
  const config = { id: 'deep-agents', sourceDir: '/tmp/deepagent_src' };
  assert.equal(
    documentId(config, '/tmp/deepagent_src/backend_teach/docs/01_state_backend.md'),
    'deep-agents-backend-teach-01-state-backend',
  );
  assert.notEqual(
    documentId(config, '/tmp/deepagent_src/memory_teach/docs/01_state_backend.md'),
    documentId(config, '/tmp/deepagent_src/backend_teach/docs/01_state_backend.md'),
  );
});

test('rejects duplicate document IDs and missing source configuration', () => {
  assert.throws(() => assertUniqueDocumentIds([{ id: 'same' }, { id: 'same' }]), /Duplicate document ID/);
  assert.throws(() => importCourse(), /Missing source directory for langgraph/);
});

test('rejects unsupported relative links', () => {
  assert.throws(() => rewriteLink('../unknown.md', 'chapter.md'), /unsupported relative link/);
});
