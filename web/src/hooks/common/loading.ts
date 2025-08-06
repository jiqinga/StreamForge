import { ref } from 'vue';

/**
 * Loading with empty initial state
 */
export function useLoadingEmpty() {
  const loading = ref(false);

  function startLoading() {
    loading.value = true;
  }

  function endLoading() {
    loading.value = false;
  }

  return {
    loading,
    startLoading,
    endLoading
  };
}
