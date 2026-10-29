import site from '../../site.config';

export { site };

export type CollectionConfig = (typeof site.collections)[number];

export function withBase(path = '/') {
  const suffix = path.startsWith('/') ? path : `/${path}`;
  return `${site.base}${suffix}`.replace(/\/{2,}/g, '/');
}

export function getCollectionConfig(collectionId: string) {
  const found = site.collections.find((c) => c.id === collectionId);
  if (!found) {
    throw new Error(`Unknown collection "${collectionId}". Defined collections: ${site.collections.map((c) => c.id).join(', ')}`);
  }
  return found;
}
