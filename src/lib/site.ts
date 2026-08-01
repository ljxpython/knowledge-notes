import site from '../../site.config';

export { site };

export function withBase(path = '/') {
  const suffix = path.startsWith('/') ? path : `/${path}`;
  return `${site.base}${suffix}`.replace(/\/{2,}/g, '/');
}
