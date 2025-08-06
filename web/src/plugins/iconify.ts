import { addAPIProvider, disableCache, enableCache } from '@iconify/vue';

/** Setup the iconify offline */
export function setupIconifyOffline() {
  const { VITE_ICONIFY_URL } = import.meta.env;

  if (VITE_ICONIFY_URL) {
    addAPIProvider('', { resources: [VITE_ICONIFY_URL] });
    disableCache('all');
  } else {
    // 完全禁用在线 API，避免网络请求
    addAPIProvider('', { resources: [] });
    enableCache('local');
  }
}
