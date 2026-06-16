// 📄 src/composables/useToast.js
import { ref } from 'vue'

// proto-core.jsx의 useToast 훅을 Vue composable로 변환.
// showToast(text, tone, icon) → 1.7초 후 자동 사라짐.
export function useToast() {
  const toast = ref(null)
  let seq = 0

  function showToast(text, tone, icon) {
    const k = ++seq
    toast.value = { text, tone, icon, k }
    setTimeout(() => {
      if (toast.value && toast.value.k === k) toast.value = null
    }, 1700)
  }

  return { toast, showToast }
}