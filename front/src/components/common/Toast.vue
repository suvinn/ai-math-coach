<!-- 📄 src/components/common/Toast.vue -->
<script setup>
import WdsIcon from './WdsIcon.vue'

// 프로토타입 PhoneLive의 토스트. AppShell 안에서 렌더됨.
// toast: { text, tone, icon, k } | null
const props = defineProps({
  toast: { type: Object, default: null },
})
</script>

<template>
  <div v-if="toast" class="ph-toast-wrap">
    <div class="ph-toast" :data-tone="toast.tone" :key="toast.k">
      <WdsIcon v-if="toast.icon" :name="toast.icon" :size="18" color="#fff" />
      {{ toast.text }}
    </div>
  </div>
</template>