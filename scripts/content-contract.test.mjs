import assert from 'node:assert/strict';
import test from 'node:test';
import { validateManifest } from './prep-content.mjs';

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
