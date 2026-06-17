<!-- 📄 src/components/common/AppBar.vue -->
<script setup>
import { computed, getCurrentInstance } from 'vue'
import { useRouter } from 'vue-router'

// 프로토타입 AppBar: 뒤로가기 + 타이틀 + 우측 action.
// action은 slot으로 받음. back 클릭은 onBack emit, 리스너 없으면 router.back().
const props = defineProps({
  title: { type: String, default: '' },
  back: { type: Boolean, default: false },
})
const emit = defineEmits(['back'])
const router = useRouter()

const instance = getCurrentInstance()
const hasBackListener = computed(() => !!instance?.vnode?.props?.onBack)

function handleBack() {
  if (hasBackListener.value) emit('back')
  else router.back()
}
</script>

<template>
  <div class="ph-appbar">
    <button v-if="back" class="ph-iconbtn" @click="handleBack" aria-label="뒤로">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M15 5l-7 7 7 7" />
      </svg>
    </button>
    <span class="title">{{ title }}</span>
    <span class="spacer" />
    <slot name="action" />
  </div>
</template>