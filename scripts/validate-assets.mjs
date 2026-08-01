import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';
import { loadManifest, validateManifest } from './prep-content.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const contentDir = resolve(root, 'content');
const publicDir = resolve(root, 'public');

validateManifest(loadManifest());

for (const file of readdirSync(contentDir).filter((entry) => entry.endsWith('.md'))) {
  const body = readFileSync(resolve(contentDir, file), 'utf8');
  for (const match of body.matchAll(/\]\((\/(?:imgs|pdfs)\/[^)\s]+)\)/g)) {
    const asset = resolve(publicDir, match[1].slice(1));
    if (!existsSync(asset)) {
      throw new Error(`${file} references missing asset ${match[1]}`);
    }
  }
}

console.log('Content and assets are valid.');
