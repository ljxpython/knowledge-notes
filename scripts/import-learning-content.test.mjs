import assert from 'node:assert/strict';
import test from 'node:test';
import { rewriteLink } from './import-learning-content.mjs';

test('rewrites chapter links to site routes', () => {
  assert.equal(
    rewriteLink('03-structured-output.md', 'test.md'),
    '/knowledge-notes/docs/langgraph-langchain/03-structured-output/',
  );
  assert.equal(
    rewriteLink('/langgraph-langchain-learning-site/docs/03-structured-output/', 'test.md'),
    '/knowledge-notes/docs/langgraph-langchain/03-structured-output/',
  );
});

test('rewrites examples and source links to GitHub', () => {
  assert.equal(
    rewriteLink('examples/01_real_model_agent.py', 'test.md'),
    'https://github.com/ljxpython/open_deep_research/blob/main/docs/langgraph-langchain-learning/examples/01_real_model_agent.py',
  );
  assert.equal(
    rewriteLink('../../src/open_deep_research/state.py', 'test.md'),
    'https://github.com/ljxpython/open_deep_research/blob/main/src/open_deep_research/state.py',
  );
});

test('rejects unsupported relative links', () => {
  assert.throws(() => rewriteLink('../unknown.md', 'chapter.md'), /unsupported relative link/);
});
