import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';
import { site } from './lib/site';

const siteBase = site.base.replace(/\/$/, '');

const resources = z.array(z.object({
  label: z.string(),
  url: z.string().refine((url) => URL.canParse(url) || url.startsWith(`${siteBase}/`), 'Expected an external URL or site-local resource path.'),
})).default([]);

const validCollectionIds = site.collections.map((c) => c.id);

const docs = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/docs' }),
  schema: z.object({
    title: z.string().min(1),
    description: z.string().min(1),
    collection: z.string().refine((val) => validCollectionIds.includes(val as any), {
      message: `collection must be one of: ${validCollectionIds.join(', ')}`,
    }),
    section: z.string().min(1).optional(),
    order: z.number().int().nonnegative().default(1),
    published: z.boolean().default(true),
    source: z.string().url().optional(),
    resources,
  }),
});

export const collections = { docs };
