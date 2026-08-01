import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const sourceDir = resolve(root, 'content');
const outputDir = resolve(root, 'src/content/docs');
const manifestPath = resolve(root, 'content.manifest.json');

export function loadManifest() {
  return JSON.parse(readFileSync(manifestPath, 'utf8'));
}

export function validateManifest(manifest) {
  if (!Array.isArray(manifest.collections) || manifest.collections.length === 0) {
    throw new Error('content.manifest.json requires a non-empty collections array.');
  }

  const collections = new Map();
  for (const collection of manifest.collections) {
    if (!collection.id || !collection.title || !collection.description || !Number.isInteger(collection.order)) {
      throw new Error('Each collection requires id, title, description, and integer order.');
    }
    if (collection.sourceUrl && !URL.canParse(collection.sourceUrl)) {
      throw new Error(`Collection "${collection.id}" has an invalid sourceUrl.`);
    }
    collections.set(collection.id, collection);
  }

  for (const [id, doc] of Object.entries(manifest.documents ?? {})) {
    if (!doc.collection || !doc.title || !doc.description || !Number.isInteger(doc.order) || typeof doc.published !== 'boolean') {
      throw new Error(`Document "${id}" requires collection, title, description, integer order, and boolean published.`);
    }
    if (!collections.has(doc.collection)) {
      throw new Error(`Document "${id}" references unknown collection "${doc.collection}".`);
    }
    if (doc.source && !URL.canParse(doc.source)) {
      throw new Error(`Document "${id}" has an invalid source URL.`);
    }
    if (!existsSync(resolve(sourceDir, `${id}.md`))) {
      throw new Error(`Document "${id}" is listed in the manifest but content/${id}.md is missing.`);
    }
    for (const resource of doc.resources ?? []) {
      if (!resource.label || !URL.canParse(resource.url)) {
        throw new Error(`Document "${id}" has an invalid resource entry.`);
      }
    }
  }
}

function yamlString(value) {
  return JSON.stringify(value);
}

export function prepareContent() {
  const manifest = loadManifest();
  validateManifest(manifest);
  rmSync(outputDir, { recursive: true, force: true });
  mkdirSync(outputDir, { recursive: true });

  for (const [id, doc] of Object.entries(manifest.documents)) {
    const collection = manifest.collections.find((item) => item.id === doc.collection);
    const body = readFileSync(resolve(sourceDir, `${id}.md`), 'utf8')
      .replace(/^#\s+.+\r?\n*/, '');
    const frontmatter = [
      '---',
      `collection: ${yamlString(collection.id)}`,
      `collectionTitle: ${yamlString(collection.title)}`,
      `collectionDescription: ${yamlString(collection.description)}`,
      `collectionOrder: ${collection.order}`,
      ...(collection.notice ? [`collectionNotice: ${yamlString(collection.notice)}`] : []),
      ...(collection.sourceLabel ? [`collectionSourceLabel: ${yamlString(collection.sourceLabel)}`] : []),
      ...(collection.sourceUrl ? [`collectionSourceUrl: ${yamlString(collection.sourceUrl)}`] : []),
      `title: ${yamlString(doc.title)}`,
      `description: ${yamlString(doc.description)}`,
      ...(doc.section ? [`section: ${yamlString(doc.section)}`] : []),
      `order: ${doc.order}`,
      `published: ${doc.published}`,
      ...(doc.source ? [`source: ${yamlString(doc.source)}`] : []),
      `resources: ${JSON.stringify(doc.resources ?? [])}`,
      '---',
      '',
    ].join('\n');
    writeFileSync(resolve(outputDir, `${id}.md`), `${frontmatter}${body}`, 'utf8');
  }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  prepareContent();
  console.log('Content prepared.');
}
