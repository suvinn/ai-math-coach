// 📄 src/composables/useToast.js
import { ref } from 'vue'

// proto-core.jsx의 useToast 훅을 Vue composable로 변환.
// showToast(text, tone, icon) → 새 토스트를 표시하고, 자동으로 사라지지 않음.
export function useToast() {
  const toast = ref(null)
  let seq = 0

  function showToast(text, tone, icon) {
    const k = ++seq
    toast.value = { text, tone, icon, k }
  }

  function hideToast() {
    toast.value = null
  }

  return { toast, showToast, hideToast }
}