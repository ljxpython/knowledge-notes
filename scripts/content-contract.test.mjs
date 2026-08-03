import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { validateManifest } from './prep-content.mjs';

const generatedManifest = JSON.parse(readFileSync(new URL('../content.manifest.json', import.meta.url), 'utf8'));

test('accepts complete document metadata', () => {
  assert.doesNotThrow(() => validateManifest({
    collections: [{ id: 'notes', title: 'Notes', description: 'Example notes.', order: 1 }],
    documents: {
      '01-real-model-agent': {
        collection: 'notes',
        title: 'Welcome',
        description: 'A valid note.',
        order: 1,
        published: true,
      },
    },
  }));
});

test('rejects incomplete document metadata', () => {
  assert.throws(() => validateManifest({
    collections: [{ id: 'notes', title: 'Notes', description: 'Example notes.', order: 1 }],
    documents: {
      broken: { title: 'Missing required fields' },
    },
  }), /requires collection/);
});

test('rejects documents in unknown collections', () => {
  assert.throws(() => validateManifest({
    collections: [{ id: 'notes', title: 'Notes', description: 'Example notes.', order: 1 }],
    documents: {
      '01-real-model-agent': {
        collection: 'missing',
        title: 'Welcome',
        description: 'A valid note.',
        order: 1,
        published: true,
      },
    },
  }), /unknown collection/);
});

test('accepts site-local example resources that exist', () => {
  assert.doesNotThrow(() => validateManifest({
    collections: [{ id: 'langgraph-langchain', title: 'Notes', description: 'Example notes.', order: 1 }],
    documents: {
      '01-real-model-agent': {
        collection: 'langgraph-langchain',
        title: 'Welcome',
        description: 'A valid note.',
        order: 1,
        published: true,
        resources: [{ label: 'Example', url: '/knowledge-notes/examples/langgraph-langchain/examples/01_real_model_agent.py' }],
      },
    },
  }));
});

test('rejects missing site-local example resources', () => {
  assert.throws(() => validateManifest({
    collections: [{ id: 'langgraph-langchain', title: 'Notes', description: 'Example notes.', order: 1 }],
    documents: {
      '01-real-model-agent': {
        collection: 'langgraph-langchain',
        title: 'Welcome',
        description: 'A valid note.',
        order: 1,
        published: true,
        resources: [{ label: 'Missing', url: '/knowledge-notes/examples/missing.py' }],
      },
    },
  }), /references missing resource/);
});

test('keeps Deep Agents topics grouped in the configured learning order', () => {
  const docs = Object.values(generatedManifest.documents).filter((doc) => doc.collection === 'deep-agents');
  const sections = [...new Set(docs.map((doc) => doc.section))];
  assert.deepEqual(sections.slice(0, 4), ['Skills', 'Memory / 记忆', 'Context Engineering', 'Backends / 后端']);
  assert.equal(docs[0].title, 'Deep Agents Skills 学习路线');
  assert.equal(docs.find((doc) => doc.section === 'Backends / 后端').title, 'Deep Agents Backends 学习笔记');
});

test('keeps non-Deep-Agent collections independent from topic grouping', () => {
  const langGraph = Object.values(generatedManifest.documents).filter((doc) => doc.collection === 'langgraph-langchain');
  const langChain = Object.values(generatedManifest.documents).filter((doc) => doc.collection === 'langchain-v1');
  assert.equal(langGraph.length, 15);
  assert.equal(langChain.length, 17);
  assert.equal(langGraph[0].section, '基础篇');
  assert.equal(langChain[0].section, 'LangChain v1');
});
